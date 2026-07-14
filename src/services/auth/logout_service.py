"""
logout_service.py
로그아웃 명령 (활성 토큰 캐시에서 제거하여 즉시 무효화)
"""

from interfaces import BaseServiceInterface
from services.ops import ServiceOp
from services.service_registry import Service


@Service(ServiceOp.AUTH_LOGOUT)
class LogoutService(BaseServiceInterface):
    def __init__(self, **services):
        self.store = services["auth_store"]

    async def call(self, payload: dict) -> dict:
        token = payload.get("token", "")
        if token not in self.store.active_tokens:
            raise ValueError("이미 로그아웃되었거나 유효하지 않은 토큰입니다.")
        self.store.active_tokens.discard(token)
        return {}
