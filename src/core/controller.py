"""
controller.py
중앙 컨트롤러 - Node.js ControlManager 구조 기반
- 인프라 계층 초기화 (DB, LLM)
- 서비스 계층 초기화 (AI, User/SSO)
- 서비스 간 의존성 주입
"""

import asyncio
import logging
from typing import Optional

from database import DatabaseService
from services import AIService, LLMService, UserService
from utils import load_config, Config

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, config: Config):
        self.config = config
        self.is_active = False

        # ── 인프라 계층 ────────────────────────
        self.db: Optional[DatabaseService] = None
        self.llm: Optional[LLMService] = None

        # ── 서비스 계층 ────────────────────────
        self.ai: Optional[AIService] = None
        self.user: Optional[UserService] = None

        # ── 백그라운드 태스크 ───────────────────
        self.background_tasks: list[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()

    # ─────────────────────────────────────────
    # Init
    # ─────────────────────────────────────────
    async def init(self) -> None:
        logger.info("=" * 50)
        logger.info("  컨트롤러 초기화 중...")
        logger.info("=" * 50)

        await self._init_infra()
        await self._init_services()
        self._inject_dependencies()
        self._start_background_tasks()

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

        llm = self.config.llm
        self.llm = LLMService(host=llm.host, port=llm.port, timeout=llm.timeout)
        if llm.auto_connect:
            try:
                await self.llm.connect()
            except Exception as e:
                logger.warning(f"[Controller] LLM 초기연결 실패 (요청 시 재시도): {e}")

        logger.info("[Controller] 인프라 계층 초기화 완료")

    async def _init_services(self) -> None:
        logger.info("[Controller] 서비스 계층 초기화 중...")
        sso = self.config.sso

        self.ai = AIService(config=self.config.ai)

        self.user = UserService(
            issuer_url=sso.issuer_url,
            client_id=sso.client_id,
            client_secret=sso.client_secret,
            algorithm=sso.algorithm,
        )
        await self.user.init()

        logger.info("[Controller] 서비스 계층 초기화 완료")

    def _inject_dependencies(self) -> None:
        logger.info("[Controller] 의존성 주입 중...")
        # 예: AI 서비스에 DB 주입 (향후 RAG 구현 시)
        # self.ai.set_db(self.db)
        logger.info("[Controller] 의존성 주입 완료")

    # ─────────────────────────────────────────
    # Background Tasks
    # ─────────────────────────────────────────
    def _start_background_tasks(self) -> None:
        self.background_tasks = [
            asyncio.create_task(self._health_monitor(), name="health_monitor"),
        ]
        logger.info(f"[Controller] 백그라운드 태스크 {len(self.background_tasks)}개 시작")

    async def _health_monitor(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                await asyncio.wait_for(self.shutdown_event.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                pass
            if self.shutdown_event.is_set():
                break
            if self.llm and not self.llm.is_connected:
                logger.warning("[Controller] LLM 끊김 → 재연결 시도")
                try:
                    await self.llm.connect()
                    logger.info("[Controller] LLM 재연결 성공")
                except Exception as e:
                    logger.error(f"[Controller] LLM 재연결 실패: {e}")

    # ─────────────────────────────────────────
    # 서비스 노출
    # ─────────────────────────────────────────
    def get_services(self) -> dict:
        return {
            "ai": self.ai,
            "llm": self.llm,
            "db": self.db,
            "user": self.user,
        }

    # ─────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────
    async def close(self) -> None:
        logger.info("=" * 50)
        logger.info("  컨트롤러 종료 중...")
        logger.info("=" * 50)

        self.is_active = False
        self.shutdown_event.set()

        for task in self.background_tasks:
            task.cancel()
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        logger.info("[Controller] 백그라운드 태스크 종료")

        if self.user:
            await self.user.close()
        if self.llm:
            await self.llm.disconnect()
        if self.db:
            await self.db.close()

        logger.info("=" * 50)
        logger.info("  컨트롤러 종료 완료 ✓")
        logger.info("=" * 50)