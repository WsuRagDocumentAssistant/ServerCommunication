"""
controller.py
- 인프라 계층 초기화 (DB)
- 서비스 상태(Store) 초기화 (Auth, SSO)
- 라우터/서비스 명령이 쓸 설정과 상태를 get_services()로 노출
"""

import logging
from typing import Optional

from database import DatabaseService
from services import AuthStore, SsoStore
from utils import load_config, Config

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, config: Config):
        self.config = config
        self.is_active = False

        # ── 인프라 계층 ────────────────────────
        self.db: Optional[DatabaseService] = None

        # ── 상태 저장소 ────────────────────────
        self.auth_store: Optional[AuthStore] = None
        self.sso_store: Optional[SsoStore] = None

    # ─────────────────────────────────────────
    # Init
    # ─────────────────────────────────────────
    async def init(self) -> None:
        logger.info("=" * 50)
        logger.info("  컨트롤러 초기화 중...")
        logger.info("=" * 50)

        await self._init_infra()
        await self._init_services()

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

    async def _init_services(self) -> None:
        logger.info("[Controller] 서비스 계층 초기화 중...")
        sso = self.config.sso
        auth = self.config.auth

        self.sso_store = SsoStore(
            issuer_url=sso.issuer_url,
            client_id=sso.client_id,
            client_secret=sso.client_secret,
            algorithm=sso.algorithm,
        )
        await self.sso_store.init()

        self.auth_store = AuthStore(
            jwt_secret=auth.jwt_secret,
            jwt_algorithm=auth.jwt_algorithm,
            jwt_expire_minutes=auth.jwt_expire_minutes,
        )

        logger.info("[Controller] 서비스 계층 초기화 완료")

    # ─────────────────────────────────────────
    # 서비스 노출
    # ─────────────────────────────────────────
    def get_services(self) -> dict:
        return {
            "db": self.db,
            "auth_store": self.auth_store,
            "sso_store": self.sso_store,
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

        if self.sso_store:
            await self.sso_store.close()
        if self.db:
            await self.db.close()

        logger.info("=" * 50)
        logger.info("  컨트롤러 종료 완료 ✓")
        logger.info("=" * 50)
