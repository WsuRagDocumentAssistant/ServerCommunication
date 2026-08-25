"""
claude_service.py
Claude(Anthropic) API 클라이언트
"""

import logging
from typing import AsyncGenerator, Optional

from ...interface import BaseLLMApiInterface
from ...schemas import AIProvider, ChatResponse

logger = logging.getLogger(__name__)


class ClaudeService(BaseLLMApiInterface):

    def __init__(self, api_key: str, default_model: str, timeout: Optional[float] = None):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)
            self._default_model = default_model
        except ImportError:
            raise RuntimeError("anthropic 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self._default_model

    def _extra_kwargs(self, temperature: Optional[float], response_format: Optional[dict]) -> dict:
        kwargs = {}
        if temperature is not None:
            # anthropic SDK의 messages.create()에는 temperature/top_p 인자 자체가 없다.
            # 그대로 넘기면 TypeError로 죽으므로 무시하고 경고만 남긴다.
            logger.warning("Claude는 temperature를 지원하지 않습니다. 무시합니다.")
        if response_format is not None:
            kwargs["output_config"] = {"format": {"type": "json_schema", "schema": response_format}}
        return kwargs

    async def chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
    ) -> ChatResponse:
        _model = model or self.default_model()
        kwargs = self._extra_kwargs(temperature, response_format)
        if system:
            kwargs["system"] = system
        message = await self._client.messages.create(
            model=_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        return ChatResponse(provider=AIProvider.CLAUDE, model=_model, content=text)

    async def stream_chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        kwargs = self._extra_kwargs(temperature, response_format)
        if system:
            kwargs["system"] = system
        async with self._client.messages.stream(
            model=_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def aclose(self) -> None:
        await self._client.close()
