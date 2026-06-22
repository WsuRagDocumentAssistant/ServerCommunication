"""
controller.py
중앙 컨트롤러 - Node.js ControlManager 구조 기반
- 인프라 계층 초기화 (DB, LLM)
- 서비스 계층 초기화 (AI, User/SSO)
- 서비스 간 의존성 주입
- WebSocket 연결 직접 처리
"""

import asyncio
import logging
from typing import Optional

from database import DatabaseService
from services import AIService, LLMService, UserService
from utils import Settings

logger = logging.getLogger(__name__)


class Controller:
    """
    중앙 컨트롤러.

    init 순서:
        1. _init_infra()          → DB, LLM (인프라 계층)
        2. _init_services()       → AI, User/SSO (서비스 계층)
        3. _inject_dependencies() → 서비스 간 의존성 주입

    shutdown 순서 (역순):
        서비스 → 인프라
    """

    def __init__(self, settings: Settings):
        self.settings = settings
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
        """인프라 계층 초기화 - DB, LLM 소켓"""
        logger.info("[Controller] 인프라 계층 초기화 중...")

        self.db = DatabaseService(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name,
            min_size=self.settings.db_pool_min,
            max_size=self.settings.db_pool_max,
        )
        if self.settings.db_auto_connect:
            try:
                await self.db.init()
            except Exception as e:
                logger.warning(f"[Controller] DB 초기연결 실패: {e}")
        else:
            logger.info("[Controller] DB auto_connect=false, 연결 건너뜀")

        self.llm = LLMService(
            host=self.settings.llm_host,
            port=self.settings.llm_port,
            timeout=self.settings.llm_timeout,
        )
        if self.settings.llm_auto_connect:
            try:
                await self.llm.connect()
            except Exception as e:
                logger.warning(f"[Controller] LLM 초기연결 실패 (요청 시 재시도): {e}")

        logger.info("[Controller] 인프라 계층 초기화 완료")

    async def _init_services(self) -> None:
        """서비스 계층 초기화 - AI, User/SSO"""
        logger.info("[Controller] 서비스 계층 초기화 중...")

        self.ai = AIService(settings=self.settings)

        self.user = UserService(
            issuer_url=self.settings.sso_issuer_url,
            client_id=self.settings.sso_client_id,
            client_secret=self.settings.sso_client_secret,
            algorithm=self.settings.sso_algorithm,
        )
        await self.user.init()

        logger.info("[Controller] 서비스 계층 초기화 완료")

    def _inject_dependencies(self) -> None:
        """서비스 간 의존성 주입"""
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
        """60초마다 LLM 소켓 상태 확인 및 자동 재연결"""
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
    # WebSocket 연결 처리
    # ─────────────────────────────────────────
    async def handle_websocket(self, websocket, client_id: str) -> None:
        client_ip = websocket.client.host if hasattr(websocket, "client") else "unknown"
        logger.info(f"[Controller] WebSocket 연결: {client_ip} → {client_id}")

        try:
            token = websocket.query_params.get("token", "")
            is_valid = await self.user.validate_token(token)
            if not is_valid:
                await websocket.close(code=4001, reason="Unauthorized")
                logger.warning(f"[Controller] WebSocket 인증 실패: {client_id}")
                return

            await websocket.accept()
            logger.info(f"[Controller] WebSocket 인증 성공: {client_id}")

            from fastapi import WebSocketDisconnect
            try:
                while True:
                    data = await websocket.receive_text()
                    processed = await self.user.on_message(client_id, data)
                    await websocket.send_text(f"[ACK] {processed}")
            except WebSocketDisconnect:
                logger.info(f"[Controller] WebSocket 연결 종료: {client_id}")

        except Exception as e:
            logger.error(f"[Controller] WebSocket 오류 {client_id}: {e}")
            try:
                await websocket.close(code=1011, reason="Server Error")
            except Exception:
                pass

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