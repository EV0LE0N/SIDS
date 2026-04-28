# services/simulator_service.py
# 特征级仿真驱动器 (Feature-level Simulator) — V2.3 架构 第二步
#
# 职责：
#   1. 基于 CORE_FEATURES 的 15 维基线模板，用正态分布扰动生成仿真流量特征
#   2. 以 asyncio 后台 Task 持续向 /api/realtime/predict-batch 推送微批数据
#   3. 暴露启动 / 停止 / 状态查询接口给 routers/simulator.py 调用
#
# 禁止事项：不引入 scapy / pcap / 数据库读写 / WebSocket

import asyncio
import logging
import random
import time
import uuid
from typing import Optional

import httpx

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from utils import CORE_FEATURES, ATTACK_LABEL_MAP

logger = logging.getLogger(__name__)

# =============================================================================
# 基线特征模板（Baseline Profiles）
#
# 说明：根据 ATTACK_LABEL_MAP 的每个类别定义一套基线浮点值。
# 数值参考 CSE-CIC-IDS2018 统计特征的量级，合理伪造即可。
# 结构：{ attack_label_value: { feature_name: baseline_float } }
# =============================================================================

# 模板键使用 ATTACK_LABEL_MAP 的值（字符串），保证数据驱动一致性
# 注意：攻击类特征相较正常流量有意做成数量级差距，确保 XGBoost 能明确识别
_BASELINE_PROFILES: dict[str, dict[str, float]] = {
    # --- Normal：正常 HTTP/HTTPS 浏览流量，双向包均衡，流量适中 ---
    ATTACK_LABEL_MAP[0]: {
        "Flow Duration":   500000.0,   # 正常会话持续时间适中 (μs)
        "Tot Fwd Pkts":       25.0,
        "Tot Bwd Pkts":       20.0,
        "TotLen Fwd Pkts":  3200.0,
        "TotLen Bwd Pkts":  8000.0,
        "Fwd Pkt Len Max":   512.0,
        "Fwd Pkt Len Min":    64.0,
        "Fwd Pkt Len Mean":  128.0,
        "Flow Byts/s":      2000.0,
        "Flow Pkts/s":        10.0,
        "Bwd Pkt Len Max":   800.0,
        "Bwd Pkt Len Min":    40.0,
        "Bwd Pkt Len Mean":  400.0,
        "Flow IAT Mean":   20000.0,
        "Flow IAT Max":   100000.0,
    },
    # --- DoS：SYN/UDP 洪泛，特征极端夸张 ---
    # 核心特征：Flow Pkts/s 和 Flow Byts/s 拉到极高，Flow Duration 极短，
    # 包长度极小且高度统一（小包洪泛），后向包几乎为零（服务端无法响应）
    ATTACK_LABEL_MAP[1]: {
        "Flow Duration":      500.0,   # 极短（μs），高频快速建连
        "Tot Fwd Pkts":     5000.0,    # 海量前向包
        "Tot Bwd Pkts":        0.0,    # 服务端完全无响应
        "TotLen Fwd Pkts": 200000.0,   # 总字节量极大
        "TotLen Bwd Pkts":     0.0,
        "Fwd Pkt Len Max":    40.0,    # SYN 包极小（40 bytes TCP头）
        "Fwd Pkt Len Min":    40.0,    # 高度统一，无正常流量的随机性
        "Fwd Pkt Len Mean":   40.0,
        "Flow Byts/s":  5000000.0,     # 5MB/s 字节率（比正常高3个数量级）
        "Flow Pkts/s":    50000.0,     # 5万包/秒（比正常高4个数量级）
        "Bwd Pkt Len Max":     0.0,
        "Bwd Pkt Len Min":     0.0,
        "Bwd Pkt Len Mean":    0.0,
        "Flow IAT Mean":      10.0,    # 包间隔极短（10μs，密集轰炸）
        "Flow IAT Max":      100.0,
    },

    # --- BruteForce：基于 DuckDB 提取的真实均值校准 ---
    # --- BruteForce：基于 DuckDB 提取的真实中位数 (Median) 纯血基线 ---
    ATTACK_LABEL_MAP[2]: {
        "Flow Duration": 6.0,
        "Tot Fwd Pkts": 1.0,
        "Tot Bwd Pkts": 1.0,
        "TotLen Fwd Pkts": 0.0,
        "TotLen Bwd Pkts": 0.0,
        "Fwd Pkt Len Max": 0.0,
        "Fwd Pkt Len Min": 0.0,
        "Fwd Pkt Len Mean": 0.0,
        "Flow Byts/s": 0.0,
        "Flow Pkts/s": 333333.3333,
        "Bwd Pkt Len Max": 0.0,
        "Bwd Pkt Len Min": 0.0,
        "Bwd Pkt Len Mean": 0.0,
        "Flow IAT Mean": 6.0,
        "Flow IAT Max": 6.0,
    },
}

# 推理目标端点（容器内自调用）
_PREDICT_ENDPOINT = "http://127.0.0.1:8000/api/realtime/predict-batch"

# 微批窗口（秒）
_BATCH_WINDOW_SEC = 0.5

# 每批记录数范围
_BATCH_MIN_RECORDS = 10
_BATCH_MAX_RECORDS = 50


# =============================================================================
# 仿真器状态（全局单例，由 router 读写）
# =============================================================================

class SimulatorState:
    """持有仿真器运行时状态，由 router 读写，由 _run_loop 更新统计"""

    def __init__(self):
        self.running: bool = False
        self.attack_type: Optional[str] = None   # 当前生成的攻击类型字符串
        self.intensity: float = 1.0              # 强度因子（预留扩展用）
        self.batches_sent: int = 0               # 累计已发送批次数
        self.records_sent: int = 0               # 累计已发送记录数
        self._task: Optional[asyncio.Task] = None

    def reset_stats(self):
        self.batches_sent = 0
        self.records_sent = 0

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "attack_type": self.attack_type,
            "intensity": self.intensity,
            "batches_sent": self.batches_sent,
            "records_sent": self.records_sent,
        }


# 全局单例
_state = SimulatorState()


# =============================================================================
# 特征生成逻辑
# =============================================================================

def _generate_feature_record(attack_type: str, intensity: float) -> dict:
    """
    基于基线模板施加正态分布扰动，生成单条 15 维特征字典。

    扰动公式：new_value = baseline * gauss(1, noise_std)，保证数值非负。
    intensity 影响噪声标准差：intensity 越大，扰动幅度越大。
    """
    baseline = _BASELINE_PROFILES[attack_type]
    # intensity 映射到 5%~20% 的扰动标准差
    noise_std = 0.05 + (intensity - 1.0) * 0.03
    noise_std = max(0.01, min(noise_std, 0.20))   # 收敛到 [1%, 20%]

    record = {}
    for feat in CORE_FEATURES:
        base_val = baseline[feat]
        # 施加乘性正态扰动，保证结果非负
        noisy_val = base_val * random.gauss(1.0, noise_std)
        record[feat] = max(0.0, round(noisy_val, 4))

    return record


def _build_source_ip() -> str:
    """生成随机仿真 IP（192.168.x.x 内网段）"""
    return f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}"


# =============================================================================
# 异步发送任务（核心后台 Loop）
# =============================================================================

async def _run_loop(attack_type: str, intensity: float):
    """
    持续微批发送任务。
    - 每 500ms 为一个窗口，生成 10~50 条记录，POST 到预测接口。
    - 捕获网络异常不中断循环（服务可能尚未就绪，容错重试）。
    - 通过 asyncio.CancelledError 响应外部取消信号，执行清理。
    """
    logger.info("仿真器启动 | 攻击类型: %s | 强度: %.2f", attack_type, intensity)

    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                batch_size = random.randint(_BATCH_MIN_RECORDS, _BATCH_MAX_RECORDS)
                records = [
                    {
                        "source_ip": _build_source_ip(),
                        "features": _generate_feature_record(attack_type, intensity),
                    }
                    for _ in range(batch_size)
                ]

                payload = {
                    "batch_id": str(uuid.uuid4()),
                    "timestamp": int(time.time()),
                    "records": records,
                }

                response = await client.post(_PREDICT_ENDPOINT, json=payload)

                if response.status_code == 200:
                    _state.batches_sent += 1
                    _state.records_sent += batch_size
                    logger.debug(
                        "批次已发送 | batch_id=%s | records=%d | 累计批次=%d",
                        payload["batch_id"], batch_size, _state.batches_sent,
                    )
                else:
                    logger.warning(
                        "批次发送响应异常 | status=%d | body=%s",
                        response.status_code, response.text[:200],
                    )

            except asyncio.CancelledError:
                # 收到外部取消信号，优雅退出
                logger.info("仿真器收到取消信号，正在停止...")
                raise   # 必须重新抛出，让 Task 正常结束
            except httpx.RequestError as e:
                # 网络连接问题（如服务重启），记录后继续等待重试
                logger.warning("批次发送网络错误（将在下一窗口重试）: %s", e)
            except Exception as e:
                logger.exception("批次发送发生未知异常: %s", e)

            # 等待下一个微批窗口
            await asyncio.sleep(_BATCH_WINDOW_SEC)


# =============================================================================
# 公开接口（供 routers/simulator.py 调用）
# =============================================================================

def get_valid_attack_types() -> list[str]:
    """返回当前系统支持的攻击类型列表（从 ATTACK_LABEL_MAP 动态生成）"""
    return list(ATTACK_LABEL_MAP.values())


async def start_simulator(attack_type: str, intensity: float = 1.0) -> None:
    """
    启动仿真器后台任务。
    如果已有任务在运行，先取消旧任务，再启动新任务。
    """
    global _state

    # 校验攻击类型合法性（必须在 ATTACK_LABEL_MAP 中）
    valid_types = get_valid_attack_types()
    if attack_type not in valid_types:
        raise ValueError(f"不合法的攻击类型 '{attack_type}'，有效值: {valid_types}")

    # 如有旧任务，先优雅取消
    if _state._task and not _state._task.done():
        logger.info("取消旧仿真任务...")
        _state._task.cancel()
        try:
            await _state._task
        except asyncio.CancelledError:
            pass

    # 重置统计并启动新任务
    _state.reset_stats()
    _state.attack_type = attack_type
    _state.intensity = intensity
    _state.running = True

    # 在当前事件循环中创建后台 Task
    _state._task = asyncio.create_task(
        _run_loop(attack_type, intensity),
        name=f"simulator_{attack_type}",
    )

    logger.info("仿真器后台任务已创建 | 攻击类型: %s", attack_type)


async def stop_simulator() -> None:
    """
    优雅停止仿真器后台任务，释放资源。
    """
    global _state

    if _state._task and not _state._task.done():
        _state._task.cancel()
        try:
            await _state._task
        except asyncio.CancelledError:
            pass
        logger.info("仿真器已停止。累计发送 %d 批次 / %d 条记录", _state.batches_sent, _state.records_sent)

    _state.running = False
    _state._task = None


def get_status() -> dict:
    """返回仿真器当前运行状态快照"""
    # 同步检查 Task 实际运行状态，防止 Task 因异常已结束但 running 标志未更新
    if _state._task and _state._task.done():
        _state.running = False

    return _state.to_dict()
