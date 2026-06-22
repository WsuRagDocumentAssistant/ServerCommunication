"""
llm_router.py
로컬 LLM 소켓 라우터 - 클래스 기반
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from schemas import LLMRequest, LLMResponse
from services import LLMService

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self, service: LLMService):
        self.service = service
        self.router = APIRouter(prefix="/llm", tags=["Local LLM"])
        self._setup_routes()

    def _setup_routes(self):
        self.router.post("/infer", response_model=LLMResponse)(self._handle_infer)
        self.router.post("/infer/stream")(self._handle_infer_stream)
        self.router.get("/status")(self._handle_status)

    async def _handle_infer(self, request: LLMRequest):
        try:
            payload = {"prompt": request.prompt, "max_tokens": request.max_tokens, "temperature": request.temperature}
            content = await self.service.send(payload)
            return LLMResponse(content=content)
        except ConnectionRefusedError:
            raise HTTPException(status_code=503, detail="로컬 LLM 서버에 연결할 수 없습니다.")
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="로컬 LLM 서버 응답 타임아웃.")
        except Exception as e:
            logger.error(f"[LLM] infer 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _handle_infer_stream(self, request: LLMRequest):
        try:
            payload = {"prompt": request.prompt, "max_tokens": request.max_tokens, "temperature": request.temperature}
            async def generator():
                async for chunk in self.service.stream_send(payload):
                    yield chunk
            return StreamingResponse(generator(), media_type="text/plain")
        except Exception as e:
            logger.error(f"[LLM] stream infer 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _handle_status(self, request: Request):
        ok = request.app.state.response["ok"]
        return ok(data={
            "connected": self.service.is_connected,
            "host": self.service.host,
            "port": self.service.port,
        })