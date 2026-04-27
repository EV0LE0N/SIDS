# routers/ws.py
# WebSocket 告警推送路由 — V2.3 架构 第四步
#
# 端点：GET /ws/alerts
# 前端通过此端点建立长连接，被动接收服务端广播的实时微批告警数据

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.ws_manager import manager

logger = logging.getLogger(__name__)

# 注意：WebSocket 路由不挂载 /api 前缀（与 HTTP 路由区分）
# 在 main.py 中以空前缀注册，最终路径为 /ws/alerts
router = APIRouter()


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    实时告警 WebSocket 端点。

    生命周期：
    1. 客户端发起握手 → connect() 接受并注册
    2. 保持连接循环，等待客户端发送消息（忽略内容，仅用于保活检测）
    3. 客户端主动断开 → WebSocketDisconnect → disconnect() 清理
    4. 网络异常 → Exception → disconnect() 清理

    注意：服务端不主动向客户端请求数据，消息流向为单向：
    realtime.py → ws_manager.broadcast() → 此连接 → 前端
    """
    await manager.connect(websocket)
    try:
        while True:
            # 阻塞等待客户端消息（心跳 / 控制帧）
            # 前端可发送任意文本（如 "ping"）维持连接，服务端忽略内容
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket 客户端正常断开")
    except Exception as e:
        logger.warning("WebSocket 连接异常终止: %s", e)
    finally:
        manager.disconnect(websocket)
