"""
ws_schemas.py
WebSocket 메시지 스키마 (확장용)
"""

from typing import Any, Optional

from pydantic import BaseModel


class WSMessage(BaseModel):
    client_id: str
    message: str
    data: Optional[Any] = None


class WSBroadcast(BaseModel):
    message: str
    data: Optional[Any] = None