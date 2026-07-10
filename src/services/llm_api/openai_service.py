"""
openai_service.py
GPT(OpenAI) API 클라이언트
"""

from typing import AsyncGenerator, Optional

from interfaces import BaseAIInterface
from schemas import AIProvider, ChatResponse


class OpenAIService(BaseAIInterface):

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
