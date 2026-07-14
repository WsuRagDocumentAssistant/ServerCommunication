"""
auth_routes.py
로그인 / 회원가입 / SSO 로그인 / 로그아웃 라우트
- 실제 처리는 services/auth/*의 @Service 명령 클래스에 위임
- REQUEST_SCHEMA로 선언된 요청은 schemas의 DTO로 검증되어 call()에 전달됨
"""

import logging

from fastapi import HTTPException

from interfaces import BaseRouteInterface
from schemas import LoginRequest, RegisterRequest, SSOLoginRequest, UserResponse, TokenResponse
from services import ServiceOp, get_service_cls
from utils.response_helper import ok, created
from .route_registry import Route

logger = logging.getLogger(__name__)


def _bearer_token(headers: dict) -> str:
    auth_header = headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1]
    return ""


@Route("POST", "/users/login", tags=["Auth"])
class LoginRoute(BaseRouteInterface):
    REQUEST_SCHEMA = LoginRequest

    def __init__(self, **services):
        self._services = services

    async def call(self, payload: LoginRequest) -> dict:
        service = get_service_cls(ServiceOp.AUTH_LOGIN)(**self._services)
        try:
            result = await service.call(payload.model_dump())
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        return ok(data=TokenResponse(access_token=result["access_token"], user=UserResponse(**result["user"])).model_dump())


@Route("POST", "/users/create/user", tags=["Auth"])
class RegisterRoute(BaseRouteInterface):
    REQUEST_SCHEMA = RegisterRequest

    def __init__(self, **services):
        self._services = services

    async def call(self, payload: RegisterRequest) -> dict:
        service = get_service_cls(ServiceOp.AUTH_REGISTER)(**self._services)
        try:
            user = await service.call(payload.model_dump())
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return created(data=UserResponse(**user).model_dump())


@Route("POST", "/users/logout", tags=["Auth"])
class LogoutRoute(BaseRouteInterface):
    def __init__(self, **services):
        self._services = services

    async def call(self, payload: dict) -> dict:
        service = get_service_cls(ServiceOp.AUTH_LOGOUT)(**self._services)
        try:
            await service.call({"token": _bearer_token(payload.get("_headers", {}))})
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        return ok(message="로그아웃되었습니다.")


@Route("POST", "/users/sso/login", tags=["Auth"])
class SsoLoginRoute(BaseRouteInterface):
    REQUEST_SCHEMA = SSOLoginRequest

    def __init__(self, **services):
        self._services = services

    async def call(self, payload: SSOLoginRequest) -> dict:
        service = get_service_cls(ServiceOp.AUTH_SSO_LOGIN)(**self._services)
        try:
            result = await service.call(payload.model_dump())
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        return ok(data=TokenResponse(access_token=result["access_token"], user=UserResponse(**result["user"])).model_dump())
