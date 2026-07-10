"""
claude_service.py
Claude(Anthropic) API 클라이언트
"""

from typing import AsyncGenerator, Optional

from interfaces import BaseAIInterface
from schemas import AIProvider, ChatResponse


class ClaudeService(BaseAIInterface):

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
