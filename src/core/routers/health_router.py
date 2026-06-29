"""
health_router.py
헬스체크 라우터 - 클래스 기반
"""

import logging

from fastapi import APIRouter

from utils.response_helper import ok

logger = logging.getLogger(__name__)


class HealthRouter:
    def __init__(self):
        self.router = APIRouter(tags=["Server"])
        self._setup_routes()

    def _setup_routes(self):
        self.router.get("/health")(self._health)

    async def _health(self):
        return ok()
