"""
user_router.py
WebSocket 연결 풀 관리 - 클래스 기반
"""

import asyncio
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 연결 풀 상태 관리"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections[client_id] = websocket
        logger.info(f"[WS] 연결 등록: {client_id} | 총 {len(self.active_connections)}개")

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            self.active_connections.pop(client_id, None)
        logger.info(f"[WS] 연결 해제: {client_id} | 총 {len(self.active_connections)}개")

    async def send_personal(self, client_id: str, message: str) -> None:
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_text(message)

    async def broadcast(self, message: str) -> None:
        disconnected: Set[str] = set()
        for client_id, ws in self.active_connections.items():
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(client_id)
        for client_id in disconnected:
            await self.disconnect(client_id)

    def get_connection_count(self) -> int:
        return len(self.active_connections)

    async def close_all(self) -> None:
        async with self._lock:
            for ws in self.active_connections.values():
                try:
                    await ws.close(code=1001, reason="Server shutting down")
                except Exception:
                    pass
            self.active_connections.clear()
        logger.info("[WS] 모든 연결 종료 완료")


# 싱글톤 - app.py에서 WebSocket 종료 시 사용
ws_manager = ConnectionManager()