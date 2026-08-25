"""
openai_service.py
GPT(OpenAI) API 클라이언트
- OpenAI 호환 HTTP 엔드포인트라면 base_url/default_headers로 다른 서버도 가리킬 수 있다
"""

from typing import AsyncGenerator, Optional

from ...interface import BaseLLMApiInterface
from ...schemas import AIProvider, ChatResponse


class OpenAIService(BaseLLMApiInterface):

    def __init__(
        self,
        api_key: str,
        default_model: str,
        base_url: Optional[str] = None,
        default_headers: Optional[dict] = None,
        timeout: Optional[float] = None,
    ):
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers=default_headers,
                timeout=timeout,
            )
            self._default_model = default_model
        except ImportError:
            raise RuntimeError("openai 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self._default_model

    def _extra_kwargs(self, temperature: Optional[float], response_format: Optional[dict]) -> dict:
        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if response_format is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": response_format, "strict": True},
            }
        return kwargs

    async def chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
    ) -> ChatResponse:
        _model = model or self.default_model()
        response = await self._client.chat.completions.create(
            model=_model, max_completion_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **self._extra_kwargs(temperature, response_format),
        )
        return ChatResponse(provider=AIProvider.GPT, model=_model, content=response.choices[0].message.content)

    async def stream_chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        stream = await self._client.chat.completions.create(
            model=_model, max_completion_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **self._extra_kwargs(temperature, response_format),
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
