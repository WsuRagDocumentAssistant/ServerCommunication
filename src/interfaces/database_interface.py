"""
database_interface.py
DatabaseService를 감싸는 프로시저 형태의 추상 인터페이스

사용법:
    class UserRepository(BaseDatabaseInterface):
        async def find_by_id(self, user_id: int) -> Optional[dict]:
            return await self._fetch_one(
                "SELECT * FROM users WHERE id = $1", user_id
            )

        async def create(self, name: str, email: str) -> dict:
            return await self._fetch_one(
                "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING *",
                name, email
            )
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from database.database_service import DatabaseService


class BaseDatabaseInterface(ABC):
    """
    도메인별 DB 접근 클래스의 기반.
    DatabaseService 인스턴스를 주입받아 내부 헬퍼(_fetch_one 등)로 노출하고,
    서브클래스는 프로시저에 해당하는 public 메서드만 구현한다.
    """

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    # ─────────────────────────────────────────
    # 내부 헬퍼 (서브클래스에서 자유롭게 호출)
    # ─────────────────────────────────────────

    async def _fetch_one(self, query: str, *args) -> Optional[dict]:
        """단일 row 조회 → dict 또는 None"""
        row = await self._db.fetchrow(query, *args)
        return dict(row) if row else None

    async def _fetch_many(self, query: str, *args) -> list[dict]:
        """다중 row 조회 → list[dict]"""
        rows = await self._db.fetch(query, *args)
        return [dict(r) for r in rows]

    async def _fetch_val(self, query: str, *args) -> Any:
        """단일 스칼라 값 조회"""
        return await self._db.fetchval(query, *args)

    async def _execute(self, query: str, *args) -> str:
        """INSERT / UPDATE / DELETE (반환값: 상태 문자열)"""
        return await self._db.execute(query, *args)

    async def _execute_many(self, query: str, args: list) -> None:
        """배치 INSERT / UPDATE"""
        await self._db.executemany(query, args)

    # ─────────────────────────────────────────
    # 트랜잭션 헬퍼
    # ─────────────────────────────────────────

    def _transaction(self):
        """트랜잭션 컨텍스트 매니저 (async with self._transaction() as conn)"""
        return self._db.transaction()

    # ─────────────────────────────────────────
    # 서브클래스가 반드시 구현해야 하는 프로시저
    # ─────────────────────────────────────────

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
