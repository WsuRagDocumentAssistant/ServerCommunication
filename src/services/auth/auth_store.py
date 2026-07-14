"""
auth_store.py
Auth 관련 명령(Service)들이 공유하는 상태
- 사용자 정보/활성 토큰을 인메모리로 보관 (서버 재시작 시 초기화)
"""

import datetime

import bcrypt
import jwt


class AuthStore:
    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256", jwt_expire_minutes: int = 1440):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expire_minutes = jwt_expire_minutes

        self.users: dict[str, dict] = {}  # email -> user
        self.active_tokens: set[str] = set()
        self.next_id = 1

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    def create_access_token(self, user: dict) -> str:
        payload = {
            "sub": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=self.jwt_expire_minutes),
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        self.active_tokens.add(token)
        return token

    def new_user(self, email: str, name: str, provider: str, password_hash: str = None) -> dict:
        user = {
            "id": self.next_id,
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "provider": provider,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        }
        self.users[email] = user
        self.next_id += 1
        return user
