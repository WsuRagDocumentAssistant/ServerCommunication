"""
validate_token_service.py
SSO 토큰 검증 명령
"""

import logging

from interfaces import BaseServiceInterface
from services.ops import ServiceOp
from services.service_registry import Service

logger = logging.getLogger(__name__)


@Service(ServiceOp.SSO_VALIDATE_TOKEN)
class ValidateTokenService(BaseServiceInterface):
    def __init__(self, **services):
        self.store = services["sso_store"]

    async def call(self, payload: dict) -> dict:
        token = payload.get("token", "")

        if not self.store.issuer_url:
            logger.debug("[ValidateTokenService] SSO 미설정 → 인증 통과 (개발 모드)")
            return {"valid": True}

        if not token:
            return {"valid": False}

        decoded = await self.store.decode_token(token)
        return {"valid": decoded is not None}
