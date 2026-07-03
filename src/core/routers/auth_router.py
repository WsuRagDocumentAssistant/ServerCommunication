"""
auth_router.py
로그인 / 회원가입 / SSO 로그인 라우터 - 클래스 기반
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from schemas import LoginRequest, RegisterRequest, SSOLoginRequest, UserResponse, TokenResponse
from services import AuthService
from utils.response_helper import ok, created

logger = logging.getLogger(__name__)

_security = HTTPBearer(auto_error=False)


class AuthRouter:
    def __init__(self, service: AuthService):
        self.service = service
        self.router = APIRouter(prefix="/users", tags=["Auth"])
        self._setup_routes()

    def _setup_routes(self):
        self.router.post("/login")(self._login)
        self.router.post("/create/user")(self._register)
        self.router.post("/logout")(self._logout)
        self.router.post("/sso/login")(self._sso_login)

    async def _login(self, request: LoginRequest):
        try:
            token, user = await self.service.login(request.email, request.password)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        return ok(data=TokenResponse(access_token=token, user=UserResponse(**user)).model_dump())

    async def _register(self, request: RegisterRequest):
        try:
            user = await self.service.register(request.email, request.password, request.name)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return created(data=UserResponse(**user).model_dump())

    async def _logout(self, credentials: HTTPAuthorizationCredentials = Depends(_security)):
        token = credentials.credentials if credentials else ""
        try:
            self.service.logout(token)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        return ok(message="로그아웃되었습니다.")

    async def _sso_login(self, request: SSOLoginRequest):
        try:
            token, user = await self.service.sso_login(request.sso_token)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        return ok(data=TokenResponse(access_token=token, user=UserResponse(**user)).model_dump())
