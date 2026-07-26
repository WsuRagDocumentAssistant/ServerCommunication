"""
base_repository_interface.py
저장소(Repository) 추상 인터페이스
- Postgres, 인메모리, Mock 등 저장 방식과 무관하게 구현체가 따라야 하는 순수 계약
- 데이터 스키마(정형/비정형)가 확정되기 전에도 이 인터페이스에 맞춰 서비스 계층을 먼저 작성할 수 있음
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseRepositoryInterface(ABC):

    @abstractmethod
    async def select_one(self, **kwargs) -> Optional[dict]:
        """단건 조회 프로시저"""
        ...

    @abstractmethod
    async def select_many(self, **kwargs) -> list[dict]:
        """다건 조회 프로시저"""
        ...

    @abstractmethod
    async def insert(self, **kwargs) -> Optional[dict]:
        """삽입 프로시저"""
        ...

    @abstractmethod
    async def update(self, **kwargs) -> Optional[dict]:
        """수정 프로시저"""
        ...

    @abstractmethod
    async def delete(self, **kwargs) -> bool:
        """삭제 프로시저 (성공 여부 반환)"""
        ...
