"""
db_schemas.py
데이터베이스 요청/응답 스키마
"""

from typing import Any

from pydantic import BaseModel


class RecordRequest(BaseModel):
    key: str
    value: Any