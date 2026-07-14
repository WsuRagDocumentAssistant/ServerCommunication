"""
get_user_info_service.py
SSO 토큰에서 사용자 정보 추출 명령
"""

from interfaces import BaseServiceInterface
from services.ops import ServiceOp
from services.service_registry import Service


@Service(ServiceOp.SSO_GET_USER_INFO)
class GetUserInfoService(BaseServiceInterface):
    def __init__(self, **services):
        self.store = services["sso_store"]

    async def call(self, payload: dict) -> dict:
        token = payload.get("token", "")
        decoded = await self.store.decode_token(token)
        if not decoded:
            return {}
        return {
            "user_id": decoded.get("sub"),
            "email": decoded.get("email"),
            "name": decoded.get("name"),
            "roles": decoded.get("roles", []),
        }
