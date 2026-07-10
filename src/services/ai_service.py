"""
ai_service.py
AI 서비스 - Claude / GPT / Gemini 구현체 + 팩토리
"""

import logging
from typing import AsyncGenerator, Optional

from interfaces import BaseAIInterface
from schemas import AIProvider, ChatResponse

logger = logging.getLogger(__name__)


class ClaudeClient(BaseAIInterface):

    def __init__(self, api_key: str, default_model: str):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
            self._default_model = default_model
        except ImportError:
            raise RuntimeError("anthropic 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self._default_model

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


class GPTClient(BaseAIInterface):

    def __init__(self, api_key: str, default_model: str):
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key)
            self._default_model = default_model
        except ImportError:
            raise RuntimeError("openai 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self._default_model

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


class GeminiClient(BaseAIInterface):

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
    def __init__(self, config):
        self._clients: dict[AIProvider, BaseAIInterface] = {}
        self._config = config

    def get(self, provider: AIProvider) -> BaseAIInterface:
        if provider not in self._clients:
            self._clients[provider] = self._build(provider)
        return self._clients[provider]

    def _build(self, provider: AIProvider) -> BaseAIInterface:
        models = self._config.default_models
        if provider == AIProvider.CLAUDE:
            return ClaudeClient(api_key=self._config.claude_api_key, default_model=models["claude"])
        elif provider == AIProvider.GPT:
            return GPTClient(api_key=self._config.openai_api_key, default_model=models["gpt"])
        elif provider == AIProvider.GEMINI:
            return GeminiClient(api_key=self._config.gemini_api_key, default_model=models["gemini"])
        raise ValueError(f"지원하지 않는 공급자: {provider}")