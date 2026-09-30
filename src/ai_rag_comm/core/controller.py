"""
controller.py
- 인프라 계층 초기화 (DB)
- LLM API(GPT)/로컬 LLM 설정을 get_services()로 노출 (실제 호출은 services/channels/*가 담당)
"""

import logging
from typing import Optional

from ..database import DatabaseService, OracleDatabaseService
from ..helpers import Config

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, config: Config):
        self.config = config
        self.is_active = False

        # ── 인프라 계층 ────────────────────────
        self.db: Optional[DatabaseService] = None
        self.school_db: Optional[OracleDatabaseService] = None

    # ─────────────────────────────────────────
    # Init
    # ─────────────────────────────────────────
    async def init(self) -> None:
        logger.info("=" * 50)
        logger.info("  컨트롤러 초기화 중...")
        logger.info("=" * 50)

        await self._init_infra()

        self.is_active = True
        logger.info("=" * 50)
        logger.info("  컨트롤러 초기화 완료 ✓")
        logger.info("=" * 50)

    async def _init_infra(self) -> None:
        logger.info("[Controller] 인프라 계층 초기화 중...")
        await self._init_postgres()
        await self._init_school_oracle()
        logger.info("[Controller] 인프라 계층 초기화 완료")

    async def _init_postgres(self) -> None:
        db = self.config.database

        try:
            self.db = DatabaseService(
                host=db.host,
                port=db.port,
                user=db.user,
                password=db.password,
                database=db.name,
                min_size=db.pool_min,
                max_size=db.pool_max,
            )
        except RuntimeError as e:
            logger.warning(f"[Controller] DB 드라이버 없음, DB 없이 진행: {e}")
            return

        if db.auto_connect:
            try:
                await self.db.init()
            except Exception as e:
                logger.warning(f"[Controller] DB 초기연결 실패: {e}")
        else:
            logger.info("[Controller] DB auto_connect=false, 연결 건너뜀")

    async def _init_school_oracle(self) -> None:
        oracle = self.config.school_oracle
        if not oracle.enabled:
            logger.info("[Controller] SCHOOL_SYNC_ENABLED=false, 학교 Oracle DB 연결 건너뜀")
            return

        try:
            school_db = OracleDatabaseService(
                host=oracle.host,
                port=oracle.port,
                service_name=oracle.service_name,
                user=oracle.user,
                password=oracle.password,
                owner=oracle.owner or None,
                min_size=oracle.pool_min,
                max_size=oracle.pool_max,
            )
        except RuntimeError as e:
            logger.warning(f"[Controller] Oracle 드라이버 없음, 학교 DB 없이 진행: {e}")
            return

        try:
            await school_db.init()
            self.school_db = school_db
        except Exception as e:
            logger.warning(f"[Controller] 학교 Oracle DB 초기연결 실패: {e}")

    # ─────────────────────────────────────────
    # 서비스 노출
    # ─────────────────────────────────────────
    def get_services(self) -> dict:
        return {
            "db": self.db,
            "school_db": self.school_db,
            "llm_api_config": self.config.llm_api,
            "local_llm_config": self.config.local_llm,
        }

    # ─────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────
    async def close(self) -> None:
        logger.info("=" * 50)
        logger.info("  컨트롤러 종료 중...")
        logger.info("=" * 50)

        self.is_active = False

        if self.db:
            await self.db.close()
        if self.school_db:
            await self.school_db.close()

        logger.info("=" * 50)
        logger.info("  컨트롤러 종료 완료 ✓")
        logger.info("=" * 50)
