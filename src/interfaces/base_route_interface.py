"""
base_route_interface.py
HTTP 라우트 핸들러 추상 인터페이스
- BaseChannelInterface와 동일한 철학: method/path가 달라도 항상 call(payload) 하나로 처리한다
- REQUEST_SCHEMA를 선언한 라우트는 payload로 검증된 DTO(Pydantic 모델) 인스턴스를 받는다
- REQUEST_SCHEMA가 없는 라우트(파일 업로드, 헤더만 쓰는 라우트 등)는 raw dict를 그대로 받는다
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRouteInterface(ABC):

    @abstractmethod
    async def call(self, payload: Any) -> dict:
        ...
