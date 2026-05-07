# routers/realtime.py
# 实时检测微批处理 API 模块 (V2.3 架构)
# 本轮更新：接入真实 XGBoost 推理 + DuckDB 微批落盘 + WebSocket 实时广播

import asyncio
import logging
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator

# 从公共配置引用核心常量，禁止在本模块中硬编码分类字符串
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from utils import CORE_FEATURES, ATTACK_LABEL_MAP

from services.model_service import batch_predict
from services import db_service
from services.ws_manager import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# Pydantic 数据模型定义
# =============================================================================

class FeatureRecord(BaseModel):
    """单条流量记录：来源 IP + 15 维核心特征向量"""
    source_ip: str
    features: dict

    @field_validator("features")
    @classmethod
    def validate_features(cls, v: dict) -> dict:
        """
        严格校验特征字典：
        1. 确保所有 CORE_FEATURES 中的键都存在（禁止特征缺失）
        2. 确保所有值都可以转换为浮点数（禁止类型错误）
        """
        missing_keys = [k for k in CORE_FEATURES if k not in v]
        if missing_keys:
            raise ValueError(
                f"特征字段缺失，共缺少 {len(missing_keys)} 个: {missing_keys}"
            )

        for key, val in v.items():
            if key not in CORE_FEATURES:
                # 忽略 CORE_FEATURES 之外的多余字段（防御性设计）
                continue
            try:
                float(val)
            except (TypeError, ValueError):
                raise ValueError(
                    f"特征 '{key}' 的值 '{val}' 无法转换为浮点数"
                )

        return v


class BatchPredictRequest(BaseModel):
    """微批预测请求体"""
    batch_id: str           # 批次唯一标识（由仿真层生成）
    timestamp: int          # Unix 时间戳（整型秒）
    records: List[FeatureRecord]

    @model_validator(mode="after")
    def validate_records_not_empty(self) -> "BatchPredictRequest":
        if not self.records:
            raise ValueError("records 列表不能为空")
        return self


class PredictResultItem(BaseModel):
    """单条预测结果"""
    ip: str
    attack_type: str        # 取值动态来自 ATTACK_LABEL_MAP.values()，禁止硬编码
    confidence: float


class BatchPredictResponse(BaseModel):
    """微批预测响应体"""
    batch_id: str
    results: List[PredictResultItem]


# =============================================================================
# API 路由实现
# =============================================================================

@router.post(
    "/realtime/predict-batch",
    response_model=BatchPredictResponse,
    summary="微批实时攻击检测",
    description="接收仿真层批量流量特征，调用 XGBoost 推理并写入 DuckDB，返回每条记录的攻击类型与置信度。",
)
async def predict_batch(request: BatchPredictRequest) -> BatchPredictResponse:
    """
    微批预测接口核心逻辑：
    1. 从请求体提取特征字典，按 CORE_FEATURES 顺序构建 DataFrame（严格对齐，防列错位）
    2. 调用 batch_predict() 获得真实 XGBoost 推理结果
    3. 拼装完整记录（元数据 + 特征 + 预测结果）写入 DuckDB
    4. 组装并返回 BatchPredictResponse
    """
    # --- Step 1: 构建特征矩阵 ---
    try:
        feature_rows = []
        for record in request.records:
            row = {feat: float(record.features[feat]) for feat in CORE_FEATURES}
            feature_rows.append(row)

        df_features = pd.DataFrame(feature_rows, columns=CORE_FEATURES)

    except KeyError as e:
        logger.error("特征提取时发生 KeyError: %s", e)
        raise HTTPException(status_code=400, detail=f"特征字段缺失: {e}")
    except (ValueError, TypeError) as e:
        logger.error("特征类型转换失败: %s", e)
        raise HTTPException(status_code=400, detail=f"特征数据类型错误: {e}")
    except Exception as e:
        logger.exception("构建特征矩阵时发生未知异常")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

    # --- Step 2: XGBoost 推理 ---
    try:
        # XGBoost 推理为 CPU 密集型同步操作，放入线程池避免阻塞主事件循环
        predictions = await asyncio.to_thread(batch_predict, df_features)
    except RuntimeError as e:
        # 模型未加载（xgb_model.json 不存在）
        logger.error("模型不可用: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("推理阶段发生异常")
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    # --- Step 3: 拼装完整 DataFrame 并落盘 DuckDB ---
    try:
        df_log = df_features.copy()
        # 在特征 DataFrame 前插入元数据列
        df_log.insert(0, "source_ip", [r.source_ip for r in request.records])
        df_log.insert(0, "timestamp", request.timestamp)
        df_log.insert(0, "batch_id", request.batch_id)
        # 追加预测结果列
        df_log["attack_type"] = [p["attack_type"] for p in predictions]
        df_log["confidence"] = [p["confidence"] for p in predictions]

        # DuckDB 写入包含磁盘 I/O 和可能的 Checkpoint，放入线程池避免阻塞主事件循环
        await asyncio.to_thread(db_service.insert_batch, df_log)

    except Exception as e:
        # DuckDB 写入失败不阻断响应，记录日志后继续返回推理结果
        # 原因：推理结果对实时展示链路更关键，存储失败不应影响业务响应
        logger.error("DuckDB 写入失败（推理结果仍正常返回）: %s", e)

    # --- Step 3.5: 异步广播 WebSocket 告警（不阻塞当前 HTTP 响应） ---
    # 使用 create_task 将广播投入事件循环后立即返回，HTTP 响应无需等待
    asyncio.create_task(_broadcast_realtime_update(request.timestamp, predictions, request.records))

    # --- Step 4: 组装响应 ---
    results = [
        PredictResultItem(
            ip=request.records[i].source_ip,
            attack_type=predictions[i]["attack_type"],
            confidence=predictions[i]["confidence"],
        )
        for i in range(len(request.records))
    ]

    return BatchPredictResponse(batch_id=request.batch_id, results=results)


# =============================================================================
# EWMA 节点级杀伤链早期探测引擎（Early Kill-Chain Detection）
#
# 设计哲学：
#   不预测"全局攻击量"（天气预报式废话），而是追踪每个 IP 在每种攻击
#   类型上的微观趋势，找出"正在冒头、即将爆发"的高危节点。
#   输出维度：按攻击类型分组的 Top N 高危节点排行榜。
#
# 内存防护：
#   采用 LRU 淘汰策略，超过 MAX_TRACKED_NODES 的节点自动被移除，
#   防止恶意 IP 池无限膨胀导致 OOM。
# =============================================================================

import time as _time
from collections import OrderedDict

# 最多追踪的 (ip, attack_type) 组合数量
_MAX_TRACKED_NODES = 500
# 每种攻击类型输出的高危节点数
_TOP_N = 3


class _NodeEWMAState:
    """单个 (ip, attack_type) 节点的 EWMA 微观状态"""
    __slots__ = ("ewma", "prev_ewma", "hit_count", "last_seen")

    def __init__(self):
        self.ewma: float = 0.0       # 当前 EWMA 平滑值
        self.prev_ewma: float = 0.0  # 上一周期 EWMA（用于计算斜率）
        self.hit_count: int = 0      # 当前批次命中次数（每批重置）
        self.last_seen: float = 0.0  # 最后活跃时间戳


class _KillChainDetector:
    """
    节点级杀伤链早期探测引擎（全局单例）。

    核心公式：
        S_t = α · X_t + (1 - α) · S_{t-1}
        Trend = S_t - S_{t-1}

    按 (ip, attack_type) 二元组独立维护 EWMA 状态。
    每次广播时，按 attack_type 分组，取 Trend 最大的 Top N 节点输出。
    """

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        # OrderedDict 实现 LRU：最近访问的移到末尾，淘汰从头部开始
        self._states: OrderedDict[tuple[str, str], _NodeEWMAState] = OrderedDict()

    def feed_batch(self, records: list, predictions: list[dict], normal_label: str) -> dict:
        """
        喂入一个完整的微批数据，更新所有节点 EWMA 并输出高危排行榜。

        Returns:
            {
                "DoS": [{"ip": "...", "trend": 0.85, "ewma": 1.2, "level": "Danger"}, ...],
                "BruteForce": [{"ip": "...", "trend": 0.42, "ewma": 0.8, "level": "Warning"}, ...]
            }
        """
        now = _time.time()

        # --- Step 1: 统计本批次每个 (ip, attack_type) 的命中数 ---
        batch_hits: dict[tuple[str, str], int] = {}
        for i, pred in enumerate(predictions):
            atype = pred["attack_type"]
            if atype == normal_label:
                continue
            ip = records[i].source_ip
            key = (ip, atype)
            batch_hits[key] = batch_hits.get(key, 0) + 1

        # --- Step 2: 更新有命中的节点 EWMA ---
        for key, count in batch_hits.items():
            state = self._states.get(key)
            if state is None:
                state = _NodeEWMAState()
                state.ewma = float(count)
                self._states[key] = state
            else:
                state.prev_ewma = state.ewma
                state.ewma = self.alpha * count + (1 - self.alpha) * state.ewma
                # LRU: 移到末尾
                self._states.move_to_end(key)
            state.hit_count = count
            state.last_seen = now

        # --- Step 3: 对本批没命中的活跃节点，EWMA 向 0 衰减 ---
        for key, state in self._states.items():
            if key not in batch_hits:
                state.prev_ewma = state.ewma
                state.ewma = (1 - self.alpha) * state.ewma
                state.hit_count = 0

        # --- Step 4: LRU 淘汰 ---
        while len(self._states) > _MAX_TRACKED_NODES:
            self._states.popitem(last=False)  # 移除最久未访问的

        # --- Step 5: 按攻击类型分组，取 Top N ---
        attack_groups: dict[str, list] = {}
        for (ip, atype), state in self._states.items():
            trend = state.ewma - state.prev_ewma
            # 只选择有正向趋势或当前活跃的节点
            if state.ewma < 0.1 and trend <= 0:
                continue
            if atype not in attack_groups:
                attack_groups[atype] = []

            # 判定威胁等级
            if trend > 0.5 or state.ewma > 3.0:
                level = "Danger"
            elif trend > 0.1 or state.ewma > 1.0:
                level = "Warning"
            else:
                level = "Watch"

            attack_groups[atype].append({
                "ip": ip,
                "trend": round(trend, 3),
                "ewma": round(state.ewma, 3),
                "level": level,
            })

        # 每组按 EWMA 值降序排列，取 Top N
        result = {}
        for atype, nodes in attack_groups.items():
            nodes.sort(key=lambda n: n["ewma"], reverse=True)
            result[atype] = nodes[:_TOP_N]

        return result


# 全局单例
_kill_chain_detector = _KillChainDetector()


# =============================================================================
# WebSocket 广播辅助协程
# 由 asyncio.create_task 在事件循环中异步执行，不阻塞 HTTP 响应
# =============================================================================

async def _broadcast_realtime_update(
    timestamp: int,
    predictions: list[dict],
    records: list,
) -> None:
    """
    构造并广播单批次实时告警包。

    推送包结构（V3.1 — 杀伤链探测升级）：
    {
        "type": "realtime_update",
        "timestamp": <int>,
        "batch_stats": { "total": N, "Normal": n, "DoS": n, "BruteForce": n },
        "predicted_targets": {
            "DoS": [{"ip": "...", "trend": 0.85, "ewma": 1.2, "level": "Danger"}, ...],
            "BruteForce": [{"ip": "...", "trend": 0.42, "ewma": 0.8, "level": "Warning"}, ...]
        },
        "alerts": [  // 仅非 Normal 的高危条目，最多 5 条
            { "ip": "...", "attack_type": "DoS", "confidence": 0.98 }
        ]
    }

    "正常流量"类型名从 ATTACK_LABEL_MAP[0] 动态读取，禁止硬编码。
    """
    import random
    try:
        # --- 动态构建批次统计，键从 ATTACK_LABEL_MAP 读取 ---
        normal_label = ATTACK_LABEL_MAP[0]   # 当前为 "Normal"，未来可能变化
        batch_stats: dict = {"total": len(predictions)}
        for label_str in ATTACK_LABEL_MAP.values():
            batch_stats[label_str] = 0
        for p in predictions:
            if p["attack_type"] in batch_stats:
                batch_stats[p["attack_type"]] += 1

        # --- 提取高危告警（非 Normal 类型），限制最多 5 条防止拥塞 ---
        alerts = [
            {
                "ip": records[i].source_ip,
                "attack_type": predictions[i]["attack_type"],
                "confidence": predictions[i]["confidence"],
            }
            for i in range(len(predictions))
            if predictions[i]["attack_type"] != normal_label
        ][:5]

        # --- 提取用于大屏飞线动画的随机流量事件（最多15条，含正常与攻击） ---
        traffic_events = [
            {
                "ip": records[i].source_ip,
                "attack_type": predictions[i]["attack_type"]
            }
            for i in range(len(predictions))
        ]
        if len(traffic_events) > 15:
            traffic_events = random.sample(traffic_events, 15)

        # --- 节点级杀伤链早期探测 ---
        predicted_targets = _kill_chain_detector.feed_batch(
            records, predictions, normal_label
        )

        payload = {
            "type": "realtime_update",
            "timestamp": timestamp,
            "batch_stats": batch_stats,
            "predicted_targets": predicted_targets,
            "alerts": alerts,
            "traffic_events": traffic_events,
        }

        await ws_manager.broadcast(payload)

    except Exception as e:
        # 广播失败只记录日志，绝不向上抛出（Task 内异常不影响主流程）
        logger.error("WebSocket 广播失败: %s", e)
