# services/simulator_service.py
# 真实流量回放引擎 (Replay Engine) — V3.0 被动雷达架构
#
# 职责：
#   1. 从真实测试集（Parquet）中按游标顺序读取流量切片
#   2. 混合所有类别的真实流量（Normal / DoS / BruteForce），模拟真实网络环境
#   3. 以 asyncio 后台 Task 持续向 /api/realtime/predict-batch 推送微批数据
#
# 设计哲学：
#   系统作为"被动雷达"运行，不选择攻击类型、不设置强度。
#   前端仅有"开启/关闭监测"开关，后端自动混播真实测试集数据。
#   XGBoost 模型"蒙眼"推理，大屏展示模型的真实判断结果。

import asyncio
import logging
import random
import time
import uuid
from typing import Optional

import httpx
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from utils import CORE_FEATURES, ATTACK_LABEL_MAP

# 封闭局域网 50 节点 IP 池（与 routers/assets.py 中的节点 IP 完全一致）
# 所有回放流量的 source_ip 都将从此池中随机选取，确保 100% 命中节点库
_NODE_IP_POOL = [f"192.168.1.{i+1}" for i in range(50)]

logger = logging.getLogger(__name__)

# =============================================================================
# 真实流量回放引擎 (Replay Engine)
#
# 从 DuckDB/Parquet 中读取真实测试集，按游标推进提取切片。
# 所有类别的数据在内存中混合，模拟真实网络中攻防流量共存的场景。
# =============================================================================

class ReplayEngine:
    """真实数据流回放引擎：加载测试集并按窗口维护游标提取切片"""
    def __init__(self):
        self.cursors = {k: 0 for k in ATTACK_LABEL_MAP.keys()}
        self.dfs = {}
        self._loaded = False
        self.total_records = 0

    def load_data(self):
        if self._loaded:
            return

        import duckdb
        DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
        PARQUET_GLOB = os.path.join(DATA_DIR, "processed/attack_data.parquet/*.parquet")

        try:
            con = duckdb.connect()
            for label_int in ATTACK_LABEL_MAP.keys():
                # 【性能与内存防护】真实数据集可能高达数 GB。
                # 作为前端态势感知大屏的回放源，此处仅抽取每类前 10000 条真实记录放入内存，
                # 通过游标循环混播，足以表现真实流量特征分布，同时彻底避免 OOM 与长时间加载卡死。
                query = f"SELECT * FROM read_parquet('{PARQUET_GLOB}') WHERE Label = {label_int} LIMIT 10000"
                df = con.execute(query).df()

                # 【零日盲测机制】严格剥离真实 Label，仅保留特征列
                if not df.empty:
                    df = df[CORE_FEATURES]

                self.dfs[label_int] = df
                self.total_records += len(df)
                logger.info("已加载真实回放测试集 | Label: %d (%s) | 记录数: %d",
                            label_int, ATTACK_LABEL_MAP[label_int], len(df))
            con.close()
            self._loaded = True
            logger.info("回放引擎就绪 | 总数据量: %d 条", self.total_records)
        except Exception as e:
            logger.error("回放引擎加载真实数据失败（请检查 Parquet 文件路径）: %s", e)

    def get_mixed_batch(self, batch_size: int) -> list[dict]:
        """
        从各类别中按真实数据集比例提取混合切片。
        混合策略：按各类别在数据集中的实际占比分配本批次条数，
        模拟真实网络中正常流量为主、攻击流量散布其中的自然分布。
        """
        if not self._loaded or self.total_records == 0:
            return []

        records = []
        for label_int, df in self.dfs.items():
            if df.empty:
                continue
            # 按实际数据占比分配条数
            ratio = len(df) / self.total_records
            count = max(1, int(batch_size * ratio))

            cursor = self.cursors.get(label_int, 0)
            if cursor + count > len(df):
                cursor = 0

            batch_df = df.iloc[cursor: cursor + count]
            self.cursors[label_int] = cursor + count
            records.extend(batch_df.to_dict(orient="records"))

        # 随机打乱，模拟真实网络流量的无序到达
        random.shuffle(records)
        return records


_engine = ReplayEngine()

# 推理目标端点（容器内自调用）
_PREDICT_ENDPOINT = "http://127.0.0.1:8000/api/realtime/predict-batch"

# 微批窗口（秒）
_BATCH_WINDOW_SEC = 0.5

# 每批记录数范围
_BATCH_MIN_RECORDS = 20
_BATCH_MAX_RECORDS = 50


# =============================================================================
# 回放引擎状态（全局单例，由 router 读写）
# =============================================================================

class ReplayState:
    """持有回放引擎运行时状态"""

    def __init__(self):
        self.running: bool = False
        self.batches_sent: int = 0
        self.records_sent: int = 0
        self._task: Optional[asyncio.Task] = None

    def reset_stats(self):
        self.batches_sent = 0
        self.records_sent = 0

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "batches_sent": self.batches_sent,
            "records_sent": self.records_sent,
        }


# 全局单例
_state = ReplayState()


def _build_source_ip() -> str:
    """从 50 节点池中随机选取 IP，确保所有流量都来自封闭局域网内的终端节点"""
    return random.choice(_NODE_IP_POOL)


# =============================================================================
# 异步发送任务（核心后台 Loop）
# =============================================================================

async def _run_loop():
    """
    持续微批发送任务（被动雷达模式）。
    - 每 500ms 为一个窗口，从真实测试集中提取混合切片
    - 所有类别的数据按其在数据集中的真实比例混合
    - XGBoost 模型自行判断每条记录的类别
    """
    logger.info("回放引擎启动 | 模式: 被动雷达（全路段混合监测）")

    # 后台异步加载真实数据（仅首次加载耗时）
    await asyncio.to_thread(_engine.load_data)

    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                batch_size = random.randint(_BATCH_MIN_RECORDS, _BATCH_MAX_RECORDS)

                # 从 ReplayEngine 提取混合真实切片
                raw_records = _engine.get_mixed_batch(batch_size)

                if not raw_records:
                    await asyncio.sleep(_BATCH_WINDOW_SEC)
                    continue

                records = [
                    {
                        "source_ip": _build_source_ip(),
                        "features": feat_dict,
                    }
                    for feat_dict in raw_records
                ]

                payload = {
                    "batch_id": str(uuid.uuid4()),
                    "timestamp": int(time.time()),
                    "records": records,
                }

                response = await client.post(_PREDICT_ENDPOINT, json=payload)

                if response.status_code == 200:
                    _state.batches_sent += 1
                    _state.records_sent += len(records)
                    logger.debug(
                        "批次已发送 | batch_id=%s | records=%d | 累计批次=%d",
                        payload["batch_id"], len(records), _state.batches_sent,
                    )
                else:
                    logger.warning(
                        "批次发送响应异常 | status=%d | body=%s",
                        response.status_code, response.text[:200],
                    )

            except asyncio.CancelledError:
                logger.info("回放引擎收到取消信号，正在停止...")
                raise
            except httpx.RequestError as e:
                logger.warning("批次发送网络错误（将在下一窗口重试）: %s", e)
            except Exception as e:
                logger.exception("批次发送发生未知异常: %s", e)

            await asyncio.sleep(_BATCH_WINDOW_SEC)


# =============================================================================
# 公开接口（供 routers/simulator.py 调用）
# =============================================================================

async def start_replay() -> None:
    """
    启动回放引擎后台任务。
    如果已有任务在运行，先取消旧任务，再启动新任务。
    """
    global _state

    if _state._task and not _state._task.done():
        logger.info("取消旧回放任务...")
        _state._task.cancel()
        try:
            await _state._task
        except asyncio.CancelledError:
            pass

    _state.reset_stats()
    _state.running = True

    _state._task = asyncio.create_task(
        _run_loop(),
        name="replay_engine",
    )

    logger.info("回放引擎后台任务已创建")


async def stop_replay() -> None:
    """优雅停止回放引擎后台任务，释放资源。"""
    global _state

    if _state._task and not _state._task.done():
        _state._task.cancel()
        try:
            await _state._task
        except asyncio.CancelledError:
            pass
        logger.info("回放引擎已停止。累计发送 %d 批次 / %d 条记录",
                     _state.batches_sent, _state.records_sent)

    _state.running = False
    _state._task = None


def get_status() -> dict:
    """返回回放引擎当前运行状态快照"""
    if _state._task and _state._task.done():
        _state.running = False

    return _state.to_dict()
