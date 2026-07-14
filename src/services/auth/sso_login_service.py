"""
sso_login_service.py
SSO 로그인 명령 - SSO 토큰 검증 후 자체 JWT 발급
"""

import logging

from interfaces import BaseServiceInterface
from services.ops import ServiceOp
from services.service_registry import Service, get_service_cls

logger = logging.getLogger(__name__)


@Service(ServiceOp.AUTH_SSO_LOGIN)
class SsoLoginService(BaseServiceInterface):
    def __init__(self, **services):
        self.store = services["auth_store"]
        self._services = services

    async def call(self, payload: dict) -> dict:
        sso_token = payload.get("sso_token")

        validate = get_service_cls(ServiceOp.SSO_VALIDATE_TOKEN)(**self._services)
        if not (await validate.call({"token": sso_token}))["valid"]:
            raise ValueError("SSO 인증에 실패했습니다.")

        get_info = get_service_cls(ServiceOp.SSO_GET_USER_INFO)(**self._services)
        info = await get_info.call({"token": sso_token})
        if not info or not info.get("email"):
            raise ValueError("SSO 사용자 정보를 확인할 수 없습니다.")

        user = self.store.users.get(info["email"])
        if not user:
            user = self.store.new_user(email=info["email"], name=info.get("name"), provider="sso")

        token = self.store.create_access_token(user)
        logger.info(f"[SsoLoginService] SSO 로그인: {info['email']}")
        return {"access_token": token, "user": user}
