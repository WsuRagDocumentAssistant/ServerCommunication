"""
database_service.py
PostgreSQL 연결 관리
- 커넥션 풀 초기화 / 종료
- 쿼리 실행 헬퍼
- 트랜잭션 관리
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

import asyncpg

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self, host: str, port: int, user: str, password: str, database: str, min_size: int = 2, max_size: int = 10):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.min_size = min_size
        self.max_size = max_size

        self._pool: Optional[asyncpg.Pool] = None
        self.is_connected = False

    async def init(self) -> None:
        logger.info("[DatabaseService] 초기화 중...")
        try:
            await self._init_connect()
            logger.info("[DatabaseService] 초기화 완료")
        except Exception as e:
            logger.error(f"[DatabaseService] 초기화 실패: {e}")
            raise

    async def _init_connect(self) -> None:
        try:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=self.min_size,
                max_size=self.max_size,
            )
            self.is_connected = True
            logger.info(f"[DatabaseService] DB 연결 성공: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            self.is_connected = False
            logger.error(f"[DatabaseService] DB 연결 실패: {e}")
            raise

    # ─────────────────────────────────────────
    # 쿼리 헬퍼
    # ─────────────────────────────────────────
    @asynccontextmanager
    async def acquire(self):
        """커넥션 획득 컨텍스트 매니저"""
        async with self._pool.acquire() as conn:
            yield conn

    async def fetch(self, query: str, *args) -> list:
        """다중 row 조회"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """단일 row 조회"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        """단일 값 조회"""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args) -> str:
        """INSERT / UPDATE / DELETE"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args: list) -> None:
        """배치 실행"""
        async with self.acquire() as conn:
            await conn.executemany(query, args)

    # ─────────────────────────────────────────
    # 트랜잭션
    # ─────────────────────────────────────────
    @asynccontextmanager
    async def transaction(self):
        """트랜잭션 컨텍스트 매니저"""
        async with self.acquire() as conn:
            async with conn.transaction():
                yield conn

    # ─────────────────────────────────────────
    # 헬스체크
    # ─────────────────────────────────────────
    async def health_check(self) -> dict:
        try:
            await self.fetchval("SELECT 1")
            return {
                "healthy": True,
                "connected": self.is_connected,
                "host": self.host,
                "database": self.database,
            }
        except Exception as e:
            return {
                "healthy": False,
                "connected": False,
                "error": str(e),
            }

    # ─────────────────────────────────────────
    # 종료
    # ─────────────────────────────────────────
    async def close(self) -> None:
        logger.info("[DatabaseService] 종료 중...")
        if self._pool:
            await self._pool.close()
            self._pool = None
        self.is_connected = False
        logger.info("[DatabaseService] 종료 완료")