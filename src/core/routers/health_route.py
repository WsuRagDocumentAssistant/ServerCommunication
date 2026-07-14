"""
health_route.py
헬스체크 라우트
"""

from interfaces import BaseRouteInterface
from utils.response_helper import ok
from .route_registry import Route


@Route("GET", "/health", tags=["Server"])
class HealthRoute(BaseRouteInterface):
    def __init__(self, **services):
        pass

    async def call(self, payload: dict) -> dict:
        return ok()
