"""
oracle_database_service.py
학교 Oracle DB 연결 관리 (python-oracledb thin 모드, Oracle Client 설치 불필요)
- DatabaseService(PostgreSQL)와 같은 메서드 이름/의미를 제공해서 BaseDatabaseInterface의
  헬퍼(_fetch_one 등)에 그대로 꽂아 쓸 수 있다
- 바인드 변수는 Oracle 문법을 쓴다: 위치 :1, :2 ... 또는 이름 :name (dict 하나를 넘기면 이름 바인드)
- 조회 결과는 dict로 반환하며, 키는 Oracle이 돌려주는 컬럼명 그대로다(따옴표 없이 만든 컬럼은 대문자)
- Windows 주의: python-oracledb의 async thin 드라이버는 Windows 기본 이벤트 루프(Proactor)와
  호환되지 않아 접속이 멈춘다. Windows에서 로컬 실행할 때는 asyncio.run() 전에
  asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())를 호출할 것
  (K8s/Linux는 해당 없음). 멈추는 대신 connect_timeout 후 실패하도록 해 두었다.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _binds(args: tuple):
    if len(args) == 1 and isinstance(args[0], dict):
        return args[0]
    return list(args)


def _dict_rows(cursor) -> None:
    columns = [d[0] for d in cursor.description]
    cursor.rowfactory = lambda *values: dict(zip(columns, values))


class OracleDatabaseService:
    def __init__(
        self, host: str, port: int, service_name: str, user: str, password: str,
        owner: Optional[str] = None, min_size: int = 1, max_size: int = 4,
        connect_timeout: float = 30.0,
    ):
        try:
            import oracledb
            self._oracledb = oracledb
        except ImportError:
            raise RuntimeError("oracledb 패키지가 설치되지 않았습니다. pip install 'ai-rag-comm[oracle]'로 설치하세요.")

        self.host = host
        self.port = port
        self.service_name = service_name
        self.user = user
        self.password = password
        self.owner = owner
        self.min_size = min_size
        self.max_size = max_size
        self.connect_timeout = connect_timeout

        self._pool: Optional[Any] = None
        self.is_connected = False

    async def init(self) -> None:
        logger.info("[OracleDatabaseService] 초기화 중...")
        try:
            self._pool = self._oracledb.create_pool_async(
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                service_name=self.service_name,
                min=self.min_size,
                max=self.max_size,
                increment=1,
            )
            # 풀 생성만으로는 접속 여부를 알 수 없어서 한 번 실제로 질의해 본다.
            await asyncio.wait_for(self.fetchval("SELECT 1 FROM DUAL"), timeout=self.connect_timeout)
            self.is_connected = True
            logger.info(f"[OracleDatabaseService] DB 연결 성공: {self.host}:{self.port}/{self.service_name}")
        except Exception as e:
            self.is_connected = False
            logger.error(f"[OracleDatabaseService] DB 연결 실패: {e}")
            if self._pool:
                # 연결이 멈춘 상태면 close도 같이 멈추므로 시간을 제한하고 풀을 버린다.
                try:
                    await asyncio.wait_for(self._pool.close(force=True), timeout=5)
                except Exception:
                    pass
                self._pool = None
            raise

    # ─────────────────────────────────────────
    # 쿼리 헬퍼
    # ─────────────────────────────────────────
    @asynccontextmanager
    async def acquire(self):
        """커넥션 획득 컨텍스트 매니저"""
        async with self._pool.acquire() as conn:
            yield conn

    async def fetch(self, query: str, *args) -> list[dict]:
        """다중 row 조회"""
        async with self.acquire() as conn:
            with conn.cursor() as cur:
                await cur.execute(query, _binds(args))
                _dict_rows(cur)
                return await cur.fetchall()

    async def fetchrow(self, query: str, *args) -> Optional[dict]:
        """단일 row 조회"""
        async with self.acquire() as conn:
            with conn.cursor() as cur:
                await cur.execute(query, _binds(args))
                _dict_rows(cur)
                return await cur.fetchone()

    async def fetchval(self, query: str, *args) -> Any:
        """단일 값 조회 (첫 row의 첫 컬럼)"""
        async with self.acquire() as conn:
            with conn.cursor() as cur:
                await cur.execute(query, _binds(args))
                row = await cur.fetchone()
                return row[0] if row else None

    async def execute(self, query: str, *args) -> int:
        """INSERT / UPDATE / DELETE — 커밋하고 영향받은 row 수를 반환"""
        async with self.acquire() as conn:
            with conn.cursor() as cur:
                await cur.execute(query, _binds(args))
                await conn.commit()
                return cur.rowcount

    async def executemany(self, query: str, args: list) -> None:
        """배치 실행 — 커밋까지 수행"""
        async with self.acquire() as conn:
            with conn.cursor() as cur:
                await cur.executemany(query, args)
                await conn.commit()

    # ─────────────────────────────────────────
    # 트랜잭션
    # ─────────────────────────────────────────
    @asynccontextmanager
    async def transaction(self):
        """트랜잭션 컨텍스트 매니저 — 블록이 정상 종료되면 커밋, 예외면 롤백"""
        async with self.acquire() as conn:
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    # ─────────────────────────────────────────
    # 헬스체크
    # ─────────────────────────────────────────
    async def health_check(self) -> dict:
        try:
            await self.fetchval("SELECT 1 FROM DUAL")
            return {
                "healthy": True,
                "connected": self.is_connected,
                "host": self.host,
                "service_name": self.service_name,
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
        logger.info("[OracleDatabaseService] 종료 중...")
        if self._pool:
            await self._pool.close()
            self._pool = None
        self.is_connected = False
        logger.info("[OracleDatabaseService] 종료 완료")
