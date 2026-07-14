"""
login_service.py
로컬 로그인 명령
"""

import logging

from interfaces import BaseServiceInterface
from services.ops import ServiceOp
from services.service_registry import Service

logger = logging.getLogger(__name__)


@Service(ServiceOp.AUTH_LOGIN)
class LoginService(BaseServiceInterface):
    def __init__(self, **services):
        self.store = services["auth_store"]

    async def call(self, payload: dict) -> dict:
        email = payload["email"]
        user = self.store.users.get(email)
        if not user or not user["password_hash"]:
            raise ValueError("이메일 또는 비밀번호가 올바르지 않습니다.")
        if not self.store.verify_password(payload["password"], user["password_hash"]):
            raise ValueError("이메일 또는 비밀번호가 올바르지 않습니다.")

        token = self.store.create_access_token(user)
        logger.info(f"[LoginService] 로그인: {email}")
        return {"access_token": token, "user": user}
