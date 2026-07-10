"""
llm_api_service.py
외부 LLM API 서비스 오케스트레이터
- 실제 프로바이더 구현체(Claude/OpenAI/Gemini)는 services/llm_api/ 에 분리되어 있음
- 이 파일은 PROVIDER_REGISTRY로 프로바이더를 조회/생성하는 역할만 담당
"""

import logging
from typing import Optional

from interfaces import BaseLLMApiInterface
from schemas import AIProvider
from services.llm_api import ClaudeService, OpenAIService, GeminiService

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 프로바이더 레지스트리
# provider별로 사용할 서비스 클래스와, config에서 api_key/기본 모델을
# 꺼내올 위치(키 이름)를 선언적으로 정의한다.
# 새 프로바이더 추가 시 services/llm_api/에 클라이언트만 만들고 여기 한 줄만 등록하면 됨.
# ─────────────────────────────────────────────
PROVIDER_REGISTRY: dict[AIProvider, dict] = {
    AIProvider.CLAUDE: {"client_cls": ClaudeService, "api_key_field": "claude_api_key", "model_key": "claude"},
    AIProvider.GPT: {"client_cls": OpenAIService, "api_key_field": "openai_api_key", "model_key": "gpt"},
    AIProvider.GEMINI: {"client_cls": GeminiService, "api_key_field": "gemini_api_key", "model_key": "gemini"},
}


class LLMApiService:
    def __init__(self, config):
        self._clients: dict[tuple, BaseLLMApiInterface] = {}
        self._config = config

    def get_llm_api(
        self,
        provider: AIProvider,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> BaseLLMApiInterface:
        """
        provider(+선택적 model/api_key 오버라이드)로 클라이언트를 조회/생성한다.
        동일 조합은 캐시된 클라이언트를 재사용한다.
        """
        cache_key = (provider, model, api_key)
        if cache_key not in self._clients:
            self._clients[cache_key] = self._build(provider, model, api_key)
        return self._clients[cache_key]

    def _build(self, provider: AIProvider, model: Optional[str], api_key: Optional[str]) -> BaseLLMApiInterface:
        entry = PROVIDER_REGISTRY.get(provider)
        if not entry:
            raise ValueError(f"지원하지 않는 공급자: {provider}")

        resolved_api_key = api_key or getattr(self._config, entry["api_key_field"])
        resolved_model = model or self._config.default_models[entry["model_key"]]

        return entry["client_cls"](api_key=resolved_api_key, default_model=resolved_model)
