"""
base_service_interface.py
도메인 서비스(Auth/SSO 등) 명령 추상 인터페이스
- BaseChannelInterface/BaseRouteInterface와 동일한 철학: 어떤 작업이든 call(payload) 하나로 처리한다
"""

from abc import ABC, abstractmethod


class BaseServiceInterface(ABC):

    @abstractmethod
    async def call(self, payload: dict) -> dict:
        ...
