"""
openai_service.py
GPT(OpenAI) API 클라이언트
- OpenAI 호환 HTTP 엔드포인트라면 base_url/default_headers로 다른 서버도 가리킬 수 있다
- enable_web_search=True면 Chat Completions가 아니라 Responses API(responses.create())로 나간다.
  OpenAI 호스팅 웹서치는 Responses API 전용 기능이라 base_url을 다른 OpenAI 호환 서버로 돌린
  상태에서 켜면 그 서버가 Responses API/웹서치를 지원하지 않는 한 동작하지 않는다.
"""

import logging
from typing import AsyncGenerator, Optional

from ...interface import BaseLLMApiInterface
from ...schemas import AIProvider, ChatResponse

logger = logging.getLogger(__name__)


class OpenAIService(BaseLLMApiInterface):

    def __init__(
        self,
        api_key: str,
        default_model: str,
        base_url: Optional[str] = None,
        default_headers: Optional[dict] = None,
        timeout: Optional[float] = None,
        enable_web_search: bool = False,
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
            self._enable_web_search = enable_web_search
        except ImportError:
            raise RuntimeError("openai 패키지가 설치되지 않았습니다.")

    def default_model(self) -> str:
        return self._default_model

    def _extra_kwargs(self, temperature: Optional[float], response_format: Optional[dict], strict: bool) -> dict:
        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if response_format is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": response_format, "strict": strict},
            }
        return kwargs

    def _messages(self, prompt: str, system: Optional[str]) -> list:
        messages = [{"role": "system", "content": system}] if system else []
        return messages + [{"role": "user", "content": prompt}]

    # ─────────────────────────────────────────
    # Chat Completions 경로 (기본)
    # ─────────────────────────────────────────
    async def _chat_completions(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float], response_format: Optional[dict], strict: bool, system: Optional[str],
    ) -> ChatResponse:
        _model = model or self.default_model()
        response = await self._client.chat.completions.create(
            model=_model, max_completion_tokens=max_tokens,
            messages=self._messages(prompt, system),
            **self._extra_kwargs(temperature, response_format, strict),
        )
        return ChatResponse(provider=AIProvider.GPT, model=_model, content=response.choices[0].message.content)

    async def _stream_chat_completions(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float], response_format: Optional[dict], strict: bool, system: Optional[str],
    ) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        stream = await self._client.chat.completions.create(
            model=_model, max_completion_tokens=max_tokens,
            messages=self._messages(prompt, system),
            stream=True,
            **self._extra_kwargs(temperature, response_format, strict),
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    # ─────────────────────────────────────────
    # Responses API 경로 (enable_web_search=True일 때만)
    # ─────────────────────────────────────────
    def _responses_kwargs(
        self, temperature: Optional[float], response_format: Optional[dict], system: Optional[str],
    ) -> dict:
        kwargs = {"tools": [{"type": "web_search"}]}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if response_format is not None:
            # Responses API는 response_format이 아니라 text.format을 쓴다. 웹서치 경로는
            # 자유 텍스트 응답을 전제로 하므로 지금은 구조화 출력을 지원하지 않고 무시한다.
            logger.warning("웹서치가 켜진 GPT 호출은 response_format을 지원하지 않습니다. 무시합니다.")
        if system:
            kwargs["instructions"] = system
        return kwargs

    async def _chat_responses(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float], response_format: Optional[dict], system: Optional[str],
    ) -> ChatResponse:
        _model = model or self.default_model()
        response = await self._client.responses.create(
            model=_model, input=prompt, max_output_tokens=max_tokens,
            **self._responses_kwargs(temperature, response_format, system),
        )
        return ChatResponse(provider=AIProvider.GPT, model=_model, content=response.output_text)

    async def _stream_chat_responses(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float], response_format: Optional[dict], system: Optional[str],
    ) -> AsyncGenerator[str, None]:
        _model = model or self.default_model()
        stream = await self._client.responses.create(
            model=_model, input=prompt, max_output_tokens=max_tokens,
            stream=True,
            **self._responses_kwargs(temperature, response_format, system),
        )
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta

    # ─────────────────────────────────────────
    # 공개 인터페이스 — enable_web_search에 따라 내부적으로 경로만 갈린다
    # ─────────────────────────────────────────
    async def chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
    ) -> ChatResponse:
        if self._enable_web_search:
            return await self._chat_responses(prompt, model, max_tokens, temperature, response_format, system)
        return await self._chat_completions(prompt, model, max_tokens, temperature, response_format, strict, system)

    async def stream_chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        if self._enable_web_search:
            async for text in self._stream_chat_responses(prompt, model, max_tokens, temperature, response_format, system):
                yield text
            return
        async for text in self._stream_chat_completions(prompt, model, max_tokens, temperature, response_format, strict, system):
            yield text

    async def aclose(self) -> None:
        await self._client.close()
