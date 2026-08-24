"""
rest_channel.py
외부 LLM API(GPT) REST 채널
- 프로바이더 조회/생성 로직(예전 llm_api_service.py)을 여기로 흡수함
- 실제 구현체는 services/llm_api/ 에 있음 (현재 GPT만 지원)
"""

from typing import AsyncGenerator, Optional, Union

from ...interface import BaseChannelInterface, BaseLLMApiInterface
from ...schemas import AIProvider
from ..llm_api import OpenAIService

# ─────────────────────────────────────────────
# 프로바이더 레지스트리
# provider별로 사용할 클라이언트 클래스와, config에서 api_key/기본 모델을
# 꺼내올 위치(키 이름)를 선언적으로 정의한다. 현재는 GPT만 등록되어 있음.
# ─────────────────────────────────────────────
PROVIDER_REGISTRY: dict[AIProvider, dict] = {
    AIProvider.GPT: {"client_cls": OpenAIService, "api_key_field": "openai_api_key", "model_key": "gpt"},
}

_client_cache: dict[tuple, BaseLLMApiInterface] = {}


def _build_client(config, provider: AIProvider, model: Optional[str], api_key: Optional[str]) -> BaseLLMApiInterface:
    cache_key = (provider, model, api_key)
    if cache_key in _client_cache:
        return _client_cache[cache_key]

    entry = PROVIDER_REGISTRY.get(provider)
    if not entry:
        raise ValueError(f"지원하지 않는 공급자: {provider}")

    resolved_api_key = api_key or getattr(config, entry["api_key_field"])
    resolved_model = model or config.default_models[entry["model_key"]]

    client = entry["client_cls"](api_key=resolved_api_key, default_model=resolved_model)
    _client_cache[cache_key] = client
    return client


class RestChannel(BaseChannelInterface):
    def __init__(
        self,
        llm_api_config,
        provider: AIProvider = AIProvider.GPT,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self._client = _build_client(llm_api_config, provider, model, api_key)

    async def call(self, payload: dict, *, stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        prompt = payload["prompt"]
        model = payload.get("model")
        max_tokens = payload.get("max_tokens", 1024)
        temperature = payload.get("temperature")

        if stream:
            return self._client.stream_chat(prompt, model, max_tokens, temperature)

        response = await self._client.chat(prompt, model, max_tokens, temperature)
        return response.content
