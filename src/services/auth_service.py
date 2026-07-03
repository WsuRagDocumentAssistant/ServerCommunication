"""
auth_service.py
로컬 로그인 / 회원가입 / SSO 로그인 처리
- 사용자 정보: 서버 메모리 캐시에 저장 (재시작 시 초기화)
- 비밀번호 해시: bcrypt
- 발급 토큰: 자체 서명 JWT (로컬 로그인 / SSO 로그인 공통)
- 로그아웃: 활성 토큰 캐시에서 제거하여 즉시 무효화
"""

import datetime
import logging

import bcrypt
import jwt

from services.sso_service import SSOService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        sso_service: SSOService,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        jwt_expire_minutes: int = 1440,
    ):
        self._sso = sso_service
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._jwt_expire_minutes = jwt_expire_minutes

        self._users: dict[str, dict] = {}  # email -> user
        self._active_tokens: set[str] = set()
        self._next_id = 1

    async def register(self, email: str, password: str, name: str) -> dict:
        if email in self._users:
            raise ValueError("이미 가입된 이메일입니다.")

        user = {
            "id": self._next_id,
            "email": email,
            "password_hash": self._hash_password(password),
            "name": name,
            "provider": "local",
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        }
        self._users[email] = user
        self._next_id += 1

        logger.info(f"[AuthService] 회원가입: {email}")
        return user

    async def login(self, email: str, password: str) -> tuple[str, dict]:
        user = self._users.get(email)
        if not user or not user["password_hash"]:
            raise ValueError("이메일 또는 비밀번호가 올바르지 않습니다.")
        if not self._verify_password(password, user["password_hash"]):
            raise ValueError("이메일 또는 비밀번호가 올바르지 않습니다.")

        token = self._create_access_token(user)
        logger.info(f"[AuthService] 로그인: {email}")
        return token, user

    async def sso_login(self, sso_token: str) -> tuple[str, dict]:
        if not await self._sso.validate_token(sso_token):
            raise ValueError("SSO 인증에 실패했습니다.")

        info = await self._sso.get_user_info(sso_token)
        if not info or not info.get("email"):
            raise ValueError("SSO 사용자 정보를 확인할 수 없습니다.")

        user = self._users.get(info["email"])
        if not user:
            user = {
                "id": self._next_id,
                "email": info["email"],
                "password_hash": None,
                "name": info.get("name"),
                "provider": "sso",
                "created_at": datetime.datetime.now(datetime.timezone.utc),
            }
            self._users[info["email"]] = user
            self._next_id += 1

        token = self._create_access_token(user)
        logger.info(f"[AuthService] SSO 로그인: {info['email']}")
        return token, user

    def logout(self, token: str) -> None:
        if token not in self._active_tokens:
            raise ValueError("이미 로그아웃되었거나 유효하지 않은 토큰입니다.")
        self._active_tokens.discard(token)

    # ─────────────────────────────────────────
    # 내부 헬퍼
    # ─────────────────────────────────────────
    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    def _create_access_token(self, user: dict) -> str:
        payload = {
            "sub": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=self._jwt_expire_minutes),
        }
        token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
        self._active_tokens.add(token)
        return token

    def decode_access_token(self, token: str) -> dict:
        if token not in self._active_tokens:
            raise ValueError("유효하지 않은 토큰입니다.")
        try:
            return jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
        except jwt.PyJWTError as e:
            self._active_tokens.discard(token)
            raise ValueError(f"유효하지 않은 토큰입니다: {e}")
