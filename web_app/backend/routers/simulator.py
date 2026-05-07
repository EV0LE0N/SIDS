# routers/simulator.py
# 回放引擎控制 API — V3.0 被动雷达架构
#
# 对外暴露三个端点（保持原有路径兼容）：
#   POST /api/simulator/start   — 启动回放引擎
#   POST /api/simulator/stop    — 停止回放引擎
#   GET  /api/simulator/status  — 查询运行状态

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.simulator_service import (
    start_replay,
    stop_replay,
    get_status,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# 响应模型
# =============================================================================

class ReplayStatusResponse(BaseModel):
    """回放引擎状态响应体"""
    running: bool
    batches_sent: int
    records_sent: int


# =============================================================================
# 路由实现
# =============================================================================

@router.post(
    "/simulator/start",
    summary="启动回放引擎",
    description="启动被动雷达模式的流量回放引擎，自动从真实测试集中混播多类型流量。",
)
async def simulator_start():
    try:
        await start_replay()
    except Exception as e:
        logger.exception("启动回放引擎时发生未知错误")
        raise HTTPException(status_code=500, detail=f"回放引擎启动失败: {str(e)}")

    return {
        "message": "回放引擎已启动，进入被动雷达监测模式",
        "status": get_status(),
    }


@router.post(
    "/simulator/stop",
    summary="停止回放引擎",
    description="优雅终止当前后台回放任务并释放资源。如引擎未在运行，幂等返回成功。",
)
async def simulator_stop():
    try:
        await stop_replay()
    except Exception as e:
        logger.exception("停止回放引擎时发生未知错误")
        raise HTTPException(status_code=500, detail=f"回放引擎停止失败: {str(e)}")

    return {
        "message": "回放引擎已停止",
        "status": get_status(),
    }


@router.get(
    "/simulator/status",
    response_model=ReplayStatusResponse,
    summary="查询回放引擎状态",
    description="返回回放引擎当前运行状态与已发送统计。",
)
async def simulator_status() -> ReplayStatusResponse:
    return ReplayStatusResponse(**get_status())
