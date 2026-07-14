"""
decode_token_service.py
자체 발급 액세스 토큰 검증/디코드 명령
"""

import jwt

from interfaces import BaseServiceInterface
from services.ops import ServiceOp
from services.service_registry import Service


@Service(ServiceOp.AUTH_DECODE_TOKEN)
class DecodeTokenService(BaseServiceInterface):
    def __init__(self, **services):
        self.store = services["auth_store"]

    async def call(self, payload: dict) -> dict:
        token = payload.get("token", "")
        if token not in self.store.active_tokens:
            raise ValueError("유효하지 않은 토큰입니다.")
        try:
            return jwt.decode(token, self.store.jwt_secret, algorithms=[self.store.jwt_algorithm])
        except jwt.PyJWTError as e:
            self.store.active_tokens.discard(token)
            raise ValueError(f"유효하지 않은 토큰입니다: {e}")
