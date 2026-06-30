"""
app.py
FastAPI 앱 클래스 - Node.js App 구조 기반
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utils.response_helper import fail
from core.routers import HealthRouter, FileRouter

logger = logging.getLogger(__name__)


class App:
    def __init__(self, controller):
        self.controller = controller
        self.fastapi_app: FastAPI = None

    def init(self) -> FastAPI:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await self.controller.init()
            self._init_routes()
            yield
            await self.controller.close()

        self.fastapi_app = FastAPI(
            title="FastAPI LLM Gateway",
            version="1.0.0",
            description="WebSocket / 외부 AI API / 로컬 LLM 통합 게이트웨이",
            lifespan=lifespan,
        )

        self._setup_middleware()
        self._setup_error_handlers()

        logger.info("[App] FastAPI 앱 초기화 완료")
        return self.fastapi_app

    def _setup_middleware(self) -> None:
        self.fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.fastapi_app.middleware("http")
        async def log_requests(request: Request, call_next):
            skip = ["/health", "/favicon.ico"]
            if not any(request.url.path.startswith(s) for s in skip):
                logger.info(f"{request.method} {request.url.path} - {request.client.host}")
            return await call_next(request)

        logger.info("[App] 미들웨어 설정 완료")

    def _init_routes(self) -> None:
        """controller.init() 완료 후 서비스를 꺼내 라우터에 주입"""
        services = self.controller.get_services()
        self.fastapi_app.state.user_service = services["user"]

        self.fastapi_app.include_router(HealthRouter().router)
        self.fastapi_app.include_router(FileRouter().router)

        logger.info("[App] 라우터 등록 완료")

    def _setup_error_handlers(self) -> None:
        @self.fastapi_app.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            return JSONResponse(
                status_code=404,
                content=fail(
                    message="요청한 경로를 찾을 수 없습니다.",
                    error_code="NOT_FOUND",
                    detail={"path": request.url.path},
                ),
            )

        @self.fastapi_app.exception_handler(500)
        async def server_error_handler(request: Request, exc):
            logger.error(f"서버 오류: {exc}")
            return JSONResponse(
                status_code=500,
                content=fail(
                    message="서버 내부 오류가 발생했습니다.",
                    error_code="INTERNAL_SERVER_ERROR",
                ),
            )

        logger.info("[App] 에러 핸들러 설정 완료")


def create_app(controller) -> FastAPI:
    return App(controller=controller).init()
