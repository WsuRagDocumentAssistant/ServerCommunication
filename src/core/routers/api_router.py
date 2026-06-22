"""
api_router.py
외부 AI API 라우터 - 클래스 기반
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from schemas import AIProvider, ChatRequest, ChatResponse
from services import AIService
from interfaces import BaseAIService

logger = logging.getLogger(__name__)


class AIRouter:
    def __init__(self, service: AIService):
        self.service = service
        self.router = APIRouter(prefix="/ai", tags=["External AI API"])
        self._setup_routes()

    def _setup_routes(self):
        self.router.post("/chat", response_model=ChatResponse)(self._handle_chat)
        self.router.post("/chat/stream")(self._handle_chat_stream)
        self.router.get("/providers")(self._handle_providers)

    async def _handle_chat(self, request: ChatRequest):
        try:
            client = self.service.get(request.provider)
            return await client.chat(request.prompt, request.model, request.max_tokens)
        except Exception as e:
            logger.error(f"[AI] chat 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _handle_chat_stream(self, request: ChatRequest):
        try:
            client = self.service.get(request.provider)
            async def generator():
                async for chunk in client.stream_chat(request.prompt, request.model, request.max_tokens):
                    yield chunk
            return StreamingResponse(generator(), media_type="text/plain")
        except Exception as e:
            logger.error(f"[AI] stream 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _handle_providers(self, request: Request):
        ok = request.app.state.response["ok"]
        return ok(data={"providers": [p.value for p in AIProvider]})