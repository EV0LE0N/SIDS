# routers/simulator.py
# 仿真器控制 API — V2.3 架构 第二步
#
# 对外暴露三个端点：
#   POST /api/simulator/start   — 启动仿真器
#   POST /api/simulator/stop    — 停止仿真器
#   GET  /api/simulator/status  — 查询运行状态

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from utils import ATTACK_LABEL_MAP

from services.simulator_service import (
    start_simulator,
    stop_simulator,
    get_status,
    get_valid_attack_types,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# 请求 / 响应模型
# =============================================================================

class SimulatorStartRequest(BaseModel):
    """启动仿真器请求体"""
    attack_type: str    # 必须在 ATTACK_LABEL_MAP.values() 中
    intensity: float = 1.0   # 生成强度，控制扰动幅度，默认 1.0

    @field_validator("attack_type")
    @classmethod
    def validate_attack_type(cls, v: str) -> str:
        """动态校验：从 ATTACK_LABEL_MAP 读取合法值，不硬编码字符串"""
        valid = list(ATTACK_LABEL_MAP.values())
        if v not in valid:
            raise ValueError(f"不合法的 attack_type '{v}'，有效值: {valid}")
        return v

    @field_validator("intensity")
    @classmethod
    def validate_intensity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("intensity 必须大于 0")
        return v


class SimulatorStatusResponse(BaseModel):
    """仿真器状态响应体"""
    running: bool
    attack_type: Optional[str]
    intensity: float
    batches_sent: int
    records_sent: int


# =============================================================================
# 路由实现
# =============================================================================

@router.post(
    "/simulator/start",
    summary="启动特征级仿真器",
    description=(
        "启动后台微批生成任务，按指定攻击类型持续向 /api/realtime/predict-batch 推送仿真流量。"
        "如已有任务运行，自动取消旧任务后启动新任务。"
    ),
)
async def simulator_start(request: SimulatorStartRequest):
    try:
        await start_simulator(
            attack_type=request.attack_type,
            intensity=request.intensity,
        )
    except ValueError as e:
        # start_simulator 内部的类型校验（与 Pydantic 校验互为双重保障）
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("启动仿真器时发生未知错误")
        raise HTTPException(status_code=500, detail=f"仿真器启动失败: {str(e)}")

    return {
        "message": f"仿真器已启动，攻击类型: {request.attack_type}，强度: {request.intensity}",
        "status": get_status(),
    }


@router.post(
    "/simulator/stop",
    summary="停止仿真器",
    description="优雅终止当前后台仿真任务并释放资源。如仿真器未在运行，幂等返回成功。",
)
async def simulator_stop():
    try:
        await stop_simulator()
    except Exception as e:
        logger.exception("停止仿真器时发生未知错误")
        raise HTTPException(status_code=500, detail=f"仿真器停止失败: {str(e)}")

    return {
        "message": "仿真器已停止",
        "status": get_status(),
    }


@router.get(
    "/simulator/status",
    response_model=SimulatorStatusResponse,
    summary="查询仿真器状态",
    description="返回仿真器当前运行状态、攻击类型、已发送批次与记录统计。",
)
async def simulator_status() -> SimulatorStatusResponse:
    return SimulatorStatusResponse(**get_status())
