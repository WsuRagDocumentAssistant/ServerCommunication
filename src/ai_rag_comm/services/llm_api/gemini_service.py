"""
gemini_service.py
Gemini(Google) API 클라이언트
- google-generativeai는 지원 종료(EOL)되어 후속 통합 SDK인 google-genai를 사용한다
"""

from typing import AsyncGenerator, Optional

from ...interface import BaseLLMApiInterface
from ...schemas import AIProvider, ChatResponse


class GeminiService(BaseLLMApiInterface):

    def __init__(self, api_key: str, default_model: str, timeout: Optional[float] = None):
        try:
            from google import genai
            http_options = genai.types.HttpOptions(timeout=int(timeout * 1000)) if timeout is not None else None
            self._client = genai.Client(api_key=api_key, http_options=http_options)
            self._genai_types = genai.types
            self._default_model = default_model
        except ImportError:
            raise RuntimeError("google-genai 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self._default_model

    def _config(
        self, max_tokens: int, temperature: Optional[float],
        response_format: Optional[dict], system: Optional[str],
    ):
        kwargs = {}
        if response_format is not None:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_json_schema"] = response_format
        if system:
            kwargs["system_instruction"] = system
        return self._genai_types.GenerateContentConfig(
            max_output_tokens=max_tokens, temperature=temperature, **kwargs,
        )

    async def chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
    ) -> ChatResponse:
        _model = model or self.default_model()
        response = await self._client.aio.models.generate_content(
            model=_model, contents=prompt,
            config=self._config(max_tokens, temperature, response_format, system),
        )
        return ChatResponse(provider=AIProvider.GEMINI, model=_model, content=response.text)

    async def stream_chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        stream = await self._client.aio.models.generate_content_stream(
            model=_model, contents=prompt,
            config=self._config(max_tokens, temperature, response_format, system),
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text

    async def aclose(self) -> None:
        await self._client.aio.aclose()
