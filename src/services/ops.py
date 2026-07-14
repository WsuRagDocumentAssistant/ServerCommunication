"""
ops.py
도메인 서비스 명령 종류 (Transport enum과 동일한 역할)
"""

from enum import Enum


class ServiceOp(str, Enum):
    AUTH_REGISTER = "auth.register"
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_SSO_LOGIN = "auth.sso_login"
    AUTH_DECODE_TOKEN = "auth.decode_token"
    SSO_VALIDATE_TOKEN = "sso.validate_token"
    SSO_GET_USER_INFO = "sso.get_user_info"
