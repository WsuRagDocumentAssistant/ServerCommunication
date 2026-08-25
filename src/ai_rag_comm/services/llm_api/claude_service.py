"""
claude_service.py
Claude(Anthropic) API 클라이언트
"""

from typing import AsyncGenerator, Optional

from ...interface import BaseLLMApiInterface
from ...schemas import AIProvider, ChatResponse


class ClaudeService(BaseLLMApiInterface):

    def __init__(self, api_key: str, default_model: str):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
            self._default_model = default_model
        except ImportError:
            raise RuntimeError("anthropic 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self._default_model

    def _extra_kwargs(self, temperature: Optional[float], response_format: Optional[dict]) -> dict:
        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if response_format is not None:
            kwargs["output_config"] = {"format": {"type": "json_schema", "schema": response_format}}
        return kwargs

    async def chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
    ) -> ChatResponse:
        _model = model or self.default_model()
        message = await self._client.messages.create(
            model=_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **self._extra_kwargs(temperature, response_format),
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        return ChatResponse(provider=AIProvider.CLAUDE, model=_model, content=text)

    async def stream_chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        async with self._client.messages.stream(
            model=_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **self._extra_kwargs(temperature, response_format),
        ) as stream:
            async for text in stream.text_stream:
                yield text
