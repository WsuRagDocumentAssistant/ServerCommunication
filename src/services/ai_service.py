"""
ai_service.py
AI 서비스 - Claude / GPT / Gemini 구현체 + 팩토리
"""

import logging
from typing import AsyncGenerator, Optional

from interfaces import BaseAIService
from schemas import AIProvider, ChatResponse

logger = logging.getLogger(__name__)


class ClaudeClient(BaseAIService):
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(self, api_key: str):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise RuntimeError("anthropic 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    async def chat(self, prompt: str, model: Optional[str], max_tokens: int) -> ChatResponse:
        _model = model or self.default_model()
        message = await self._client.messages.create(
            model=_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return ChatResponse(provider=AIProvider.CLAUDE, model=_model, content=message.content[0].text)

    async def stream_chat(self, prompt: str, model: Optional[str], max_tokens: int) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        async with self._client.messages.stream(
            model=_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text


class GPTClient(BaseAIService):
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key: str):
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise RuntimeError("openai 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    async def chat(self, prompt: str, model: Optional[str], max_tokens: int) -> ChatResponse:
        _model = model or self.default_model()
        response = await self._client.chat.completions.create(
            model=_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return ChatResponse(provider=AIProvider.GPT, model=_model, content=response.choices[0].message.content)

    async def stream_chat(self, prompt: str, model: Optional[str], max_tokens: int) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        stream = await self._client.chat.completions.create(
            model=_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class GeminiClient(BaseAIService):
    DEFAULT_MODEL = "gemini-1.5-pro"

    def __init__(self, api_key: str):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._genai = genai
        except ImportError:
            raise RuntimeError("google-generativeai 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    async def chat(self, prompt: str, model: Optional[str], max_tokens: int) -> ChatResponse:
        import asyncio
        _model = model or self.default_model()
        gm = self._genai.GenerativeModel(_model)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: gm.generate_content(prompt))
        return ChatResponse(provider=AIProvider.GEMINI, model=_model, content=response.text)

    async def stream_chat(self, prompt: str, model: Optional[str], max_tokens: int) -> AsyncGenerator[str, None]:
        import asyncio
        _model = model or self.default_model()
        gm = self._genai.GenerativeModel(_model)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: gm.generate_content(prompt, stream=True))
        for chunk in response:
            yield chunk.text


class AIService:
    def __init__(self, settings):
        self._clients: dict[AIProvider, BaseAIService] = {}
        self._settings = settings

    def get(self, provider: AIProvider) -> BaseAIService:
        if provider not in self._clients:
            self._clients[provider] = self._build(provider)
        return self._clients[provider]

    def _build(self, provider: AIProvider) -> BaseAIService:
        if provider == AIProvider.CLAUDE:
            return ClaudeClient(api_key=self._settings.claude_api_key)
        elif provider == AIProvider.GPT:
            return GPTClient(api_key=self._settings.openai_api_key)
        elif provider == AIProvider.GEMINI:
            return GeminiClient(api_key=self._settings.gemini_api_key)
        raise ValueError(f"지원하지 않는 공급자: {provider}")