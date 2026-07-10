"""
gemini_service.py
Gemini(Google) API 클라이언트
"""

import asyncio
from typing import AsyncGenerator, Optional

from interfaces import BaseLLMApiInterface
from schemas import AIProvider, ChatResponse


class GeminiService(BaseLLMApiInterface):

    def __init__(self, api_key: str, default_model: str):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._genai = genai
            self._default_model = default_model
        except ImportError:
            raise RuntimeError("google-generativeai 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self._default_model

    async def chat(self, prompt: str, model: Optional[str], max_tokens: int) -> ChatResponse:
        _model = model or self.default_model()
        gm = self._genai.GenerativeModel(_model)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: gm.generate_content(prompt))
        return ChatResponse(provider=AIProvider.GEMINI, model=_model, content=response.text)

    async def stream_chat(self, prompt: str, model: Optional[str], max_tokens: int) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        gm = self._genai.GenerativeModel(_model)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: gm.generate_content(prompt, stream=True))
        for chunk in response:
            yield chunk.text
