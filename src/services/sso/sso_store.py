"""
sso_store.py
SSO 관련 명령(Service)들이 공유하는 상태
- JWKS 캐시 보관, 토큰 디코드 헬퍼 제공
- init()/close()는 요청 단위 명령이 아니라 서버 생명주기 훅이라 call() 밖에 둠
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SsoStore:
    def __init__(self, issuer_url: str, client_id: str, client_secret: str, algorithm: str = "RS256"):
        self.issuer_url = issuer_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.algorithm = algorithm
        self.jwks: Optional[dict] = None

    async def init(self) -> None:
        if not self.issuer_url:
            logger.info("[SsoStore] SSO issuer_url 미설정 → 인증 스킵 모드")
            return
        try:
            await self._fetch_jwks()
            logger.info(f"[SsoStore] SSO 초기화 완료: {self.issuer_url}")
        except Exception as e:
            logger.warning(f"[SsoStore] JWKS 초기화 실패 (요청 시 재시도): {e}")

    async def close(self) -> None:
        self.jwks = None
        logger.info("[SsoStore] 종료 완료")

    async def _fetch_jwks(self) -> None:
        import httpx
        jwks_url = f"{self.issuer_url}/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            self.jwks = response.json()
        logger.info("[SsoStore] JWKS 공개키 로드 완료")

    async def decode_token(self, token: str) -> Optional[dict]:
        try:
            import jwt
            if self.algorithm == "RS256":
                if not self.jwks:
                    await self._fetch_jwks()
                from jwt import PyJWKClient
                jwks_client = PyJWKClient(f"{self.issuer_url}/.well-known/jwks.json")
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                return jwt.decode(token, signing_key.key, algorithms=[self.algorithm], audience=self.client_id)
            return jwt.decode(token, self.client_secret, algorithms=[self.algorithm], audience=self.client_id)
        except Exception as e:
            logger.warning(f"[SsoStore] JWT 디코드 실패: {e}")
            return None
