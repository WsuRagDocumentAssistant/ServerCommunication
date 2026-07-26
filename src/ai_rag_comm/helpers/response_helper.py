"""
response_helper.py
공통 HTTP 응답 헬퍼
- 전체 라우터에서 일관된 응답 포맷 사용
- 성공 / 실패 / 페이지네이션 응답 통일
"""

from typing import Any, Optional
from pydantic import BaseModel


# ─────────────────────────────────────────────
# 공통 응답 스키마
# ─────────────────────────────────────────────
class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    detail: Optional[Any] = None


# ─────────────────────────────────────────────
# 응답 생성 팩토리 함수
# ─────────────────────────────────────────────
def ok(data: Any = None, message: str = "success") -> dict:
    """성공 응답"""
    return BaseResponse(success=True, message=message, data=data).model_dump()


def fail(
    message: str,
    error_code: Optional[str] = None,
    detail: Optional[Any] = None,
) -> dict:
    """실패 응답"""
    return ErrorResponse(
        success=False,
        message=message,
        error_code=error_code,
        detail=detail,
    ).model_dump()


def created(data: Any = None, message: str = "created") -> dict:
    """생성 성공 응답"""
    return ok(data=data, message=message)


def deleted(key: str) -> dict:
    """삭제 성공 응답"""
    return ok(data={"key": key}, message="deleted")