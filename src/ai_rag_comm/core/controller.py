"""
controller.py
- 인프라 계층 초기화 (DB)
- LLM API(GPT)/로컬 LLM 설정을 get_services()로 노출 (실제 호출은 services/channels/*가 담당)
"""

import logging
from typing import Optional

from ..database import DatabaseService
from ..helpers import Config

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, config: Config):
        self.config = config
        self.is_active = False

        # ── 인프라 계층 ────────────────────────
        self.db: Optional[DatabaseService] = None

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
        db = self.config.database

        self.db = DatabaseService(
            host=db.host,
            port=db.port,
            user=db.user,
            password=db.password,
            database=db.name,
            min_size=db.pool_min,
            max_size=db.pool_max,
        )
        if db.auto_connect:
            try:
                await self.db.init()
            except Exception as e:
                logger.warning(f"[Controller] DB 초기연결 실패: {e}")
        else:
            logger.info("[Controller] DB auto_connect=false, 연결 건너뜀")

        logger.info("[Controller] 인프라 계층 초기화 완료")

    # ─────────────────────────────────────────
    # 서비스 노출
    # ─────────────────────────────────────────
    def get_services(self) -> dict:
        return {
            "db": self.db,
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

        logger.info("=" * 50)
        logger.info("  컨트롤러 종료 완료 ✓")
        logger.info("=" * 50)
