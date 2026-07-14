"""
register_service.py
회원가입 명령
"""

import logging

from interfaces import BaseServiceInterface
from services.ops import ServiceOp
from services.service_registry import Service

logger = logging.getLogger(__name__)


@Service(ServiceOp.AUTH_REGISTER)
class RegisterService(BaseServiceInterface):
    def __init__(self, **services):
        self.store = services["auth_store"]

    async def call(self, payload: dict) -> dict:
        email = payload["email"]
        if email in self.store.users:
            raise ValueError("이미 가입된 이메일입니다.")

        user = self.store.new_user(
            email=email,
            name=payload.get("name"),
            provider="local",
            password_hash=self.store.hash_password(payload["password"]),
        )
        logger.info(f"[RegisterService] 회원가입: {email}")
        return user
