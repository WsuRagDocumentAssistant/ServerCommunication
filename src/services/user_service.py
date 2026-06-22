"""
user_service.py
SSO 인증 서비스
- JWT 토큰 검증 (RS256/HS256)
- 사용자 정보 추출
- WebSocket 연결 인증
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class UserService:
    """SSO 인증 담당 서비스"""

    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str,
        algorithm: str = "RS256",
    ):
        self._issuer_url = issuer_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._algorithm = algorithm
        self._jwks = None  # JWKS 캐시

    async def init(self) -> None:
        """JWKS 공개키 초기화"""
        if not self._issuer_url:
            logger.info("[UserService] SSO issuer_url 미설정 → 인증 스킵 모드")
            return
        try:
            await self._fetch_jwks()
            logger.info(f"[UserService] SSO 초기화 완료: {self._issuer_url}")
        except Exception as e:
            logger.warning(f"[UserService] JWKS 초기화 실패 (요청 시 재시도): {e}")

    async def _fetch_jwks(self) -> None:
        """JWKS 공개키 fetch"""
        import httpx
        jwks_url = f"{self._issuer_url}/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            self._jwks = response.json()
        logger.info("[UserService] JWKS 공개키 로드 완료")

    async def validate_token(self, token: str) -> bool:
        """
        JWT 토큰 검증.
        SSO 미설정 시 항상 True 반환 (개발 모드).
        """
        if not self._issuer_url:
            logger.debug("[UserService] SSO 미설정 → 인증 통과 (개발 모드)")
            return True

        if not token:
            logger.warning("[UserService] 토큰 없음")
            return False

        try:
            payload = await self._decode_token(token)
            return payload is not None
        except Exception as e:
            logger.warning(f"[UserService] 토큰 검증 실패: {e}")
            return False

    async def _decode_token(self, token: str) -> Optional[dict]:
        """JWT 디코드 및 검증"""
        try:
            import jwt
            if self._algorithm == "RS256":
                if not self._jwks:
                    await self._fetch_jwks()
                # JWKS에서 공개키 추출
                from jwt import PyJWKClient
                jwks_client = PyJWKClient(f"{self._issuer_url}/.well-known/jwks.json")
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=[self._algorithm],
                    audience=self._client_id,
                )
            else:
                # HS256
                payload = jwt.decode(
                    token,
                    self._client_secret,
                    algorithms=[self._algorithm],
                    audience=self._client_id,
                )
            return payload
        except Exception as e:
            logger.warning(f"[UserService] JWT 디코드 실패: {e}")
            return None

    async def get_user_info(self, token: str) -> Optional[dict]:
        """토큰에서 사용자 정보 추출"""
        payload = await self._decode_token(token)
        if not payload:
            return None
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "roles": payload.get("roles", []),
        }

    async def on_message(self, client_id: str, message: str) -> str:
        """WebSocket 메시지 처리 (확장용)"""
        logger.debug(f"[UserService] 메시지: {client_id} → {message}")
        return message

    async def close(self) -> None:
        self._jwks = None
        logger.info("[UserService] 종료 완료")