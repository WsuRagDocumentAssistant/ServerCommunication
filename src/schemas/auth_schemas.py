"""
auth_schemas.py
로그인 / 회원가입 / SSO 요청·응답 스키마
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class SSOLoginRequest(BaseModel):
    sso_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    provider: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
