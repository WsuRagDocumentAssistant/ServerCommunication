"""
rest_channel.py
외부 LLM API(GPT/Claude/Gemini) REST 채널
- 프로바이더 조회/생성 로직(예전 llm_api_service.py)을 여기로 흡수함
- 실제 구현체는 services/llm_api/ 에 있음
"""

import logging
from typing import AsyncGenerator, Optional, Union

from ...interface import BaseChannelInterface, BaseLLMApiInterface
from ...schemas import AIProvider
from ..llm_api import OpenAIService, ClaudeService, GeminiService

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 프로바이더 레지스트리
# provider별로 사용할 클라이언트 클래스와, config에서 api_key/기본 모델을
# 꺼내올 위치(키 이름)를 선언적으로 정의한다.
# supports_web_search: 그 provider의 client_cls가 enable_web_search 생성자 인자를
# 받는지 여부. GPT는 chat.completions.create()로는 OpenAI 호스팅 웹서치를 쓸 수
# 없어서(Responses API 전용 기능) 아직 지원하지 않는다.
# ─────────────────────────────────────────────
PROVIDER_REGISTRY: dict[AIProvider, dict] = {
    AIProvider.GPT: {
        "client_cls": OpenAIService, "api_key_field": "openai_api_key",
        "model_key": "gpt", "supports_web_search": False,
    },
    AIProvider.CLAUDE: {
        "client_cls": ClaudeService, "api_key_field": "anthropic_api_key",
        "model_key": "claude", "supports_web_search": True,
    },
    AIProvider.GEMINI: {
        "client_cls": GeminiService, "api_key_field": "gemini_api_key",
        "model_key": "gemini", "supports_web_search": True,
    },
}

_client_cache: dict[tuple, BaseLLMApiInterface] = {}


def _build_client(
    config, provider: AIProvider, model: Optional[str], api_key: Optional[str],
    enable_web_search: bool,
) -> BaseLLMApiInterface:
    cache_key = (provider, model, api_key, enable_web_search)
    if cache_key in _client_cache:
        return _client_cache[cache_key]

    entry = PROVIDER_REGISTRY.get(provider)
    if not entry:
        raise ValueError(f"지원하지 않는 공급자: {provider}")

    resolved_api_key = api_key or getattr(config, entry["api_key_field"])
    resolved_model = model or config.default_models[entry["model_key"]]

    kwargs = {"api_key": resolved_api_key, "default_model": resolved_model, "timeout": config.timeout}
    if entry["supports_web_search"]:
        kwargs["enable_web_search"] = enable_web_search
    elif enable_web_search:
        logger.warning(f"{provider}는 웹서치를 지원하지 않습니다. 무시합니다.")

    client = entry["client_cls"](**kwargs)
    _client_cache[cache_key] = client
    return client


class RestChannel(BaseChannelInterface):
    def __init__(
        self,
        llm_api_config,
        provider: AIProvider = AIProvider.GPT,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        enable_web_search: bool = False,
    ):
        self._client = _build_client(llm_api_config, provider, model, api_key, enable_web_search)

    async def call(self, payload: dict, *, stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        prompt = payload["prompt"]
        model = payload.get("model")
        max_tokens = payload.get("max_tokens", 1024)
        temperature = payload.get("temperature")
        response_format = payload.get("response_format")
        strict = payload.get("strict", True)
        system = payload.get("system")

        if stream:
            return self._client.stream_chat(prompt, model, max_tokens, temperature, response_format, strict, system)

        response = await self._client.chat(prompt, model, max_tokens, temperature, response_format, strict, system)
        return response.content
