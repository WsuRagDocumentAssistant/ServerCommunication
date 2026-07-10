"""
base_database_interface.py
PostgreSQL(DatabaseService) 기반 Repository를 위한 추상 베이스
- BaseRepositoryInterface 인터페이스를 구현하며, Postgres 전용 쿼리 헬퍼를 추가로 제공한다

사용법:
    class UserRepository(BaseDatabaseInterface):
        async def select_one(self, **kwargs) -> Optional[dict]:
            return await self._fetch_one(
                "SELECT * FROM users WHERE id = $1", kwargs["id"]
            )

        async def insert(self, **kwargs) -> dict:
            return await self._fetch_one(
                "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING *",
                kwargs["name"], kwargs["email"]
            )
"""

from typing import Any, Optional

from database.database_service import DatabaseService
from interfaces.base_repository_interface import BaseRepositoryInterface


class BaseDatabaseInterface(BaseRepositoryInterface):
    """
    Postgres 기반 Repository의 공통 베이스.
    DatabaseService 인스턴스를 주입받아 내부 헬퍼(_fetch_one 등)로 노출하고,
    서브클래스는 BaseRepositoryInterface의 프로시저(select_one 등)만 구현한다.
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

    # select_one / select_many / insert / update / delete 는
    # BaseRepositoryInterface에서 상속되는 추상 프로시저이며, 서브클래스가 구현해야 한다.
