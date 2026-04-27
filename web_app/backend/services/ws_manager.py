# services/ws_manager.py
# WebSocket 连接管理器 — V2.3 架构 第四步
#
# 设计原则：
#   - 纯内存管理，不依赖 Redis / MQ 等外部组件
#   - 全局单例，所有路由共享同一个连接池
#   - broadcast 失败时仅移除失效连接，不影响其他客户端

import asyncio
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket 连接管理器（全局单例）。

    职责：
    - 维护当前所有活跃 WebSocket 连接的集合
    - 提供连接注册 / 注销 / 广播接口
    - broadcast 使用 asyncio.gather 并发推送，单客户端失败不阻塞整体
    """

    def __init__(self):
        # 使用 set 而非 list，O(1) 删除，防重复注册
        self._active: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """接受握手并注册连接。"""
        await websocket.accept()
        self._active.add(websocket)
        logger.info("WebSocket 客户端已连接，当前连接数: %d", len(self._active))

    def disconnect(self, websocket: WebSocket) -> None:
        """移除连接（幂等，连接不存在时不报错）。"""
        self._active.discard(websocket)
        logger.info("WebSocket 客户端已断开，当前连接数: %d", len(self._active))

    async def broadcast(self, message: dict) -> None:
        """
        向所有活跃客户端并发广播 JSON 消息。

        - 使用 asyncio.gather 并发发送，不串行等待
        - 任何单个客户端发送失败，仅将其从连接池中移除，不影响其他客户端
        - 如果当前无连接，直接返回（零开销）
        """
        if not self._active:
            return

        # 快照当前连接集合，防止在发送过程中集合被并发修改
        targets = list(self._active)
        dead: list[WebSocket] = []

        async def _send_one(ws: WebSocket) -> None:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning("WebSocket 发送失败，将移除该连接: %s", e)
                dead.append(ws)

        await asyncio.gather(*[_send_one(ws) for ws in targets])

        # 清理失效连接
        for ws in dead:
            self._active.discard(ws)


# 全局单例——所有路由模块 import 此实例
manager = ConnectionManager()
