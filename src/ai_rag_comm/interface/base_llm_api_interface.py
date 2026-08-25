"""
base_llm_api_interface.py
외부 LLM API(Claude/GPT/Gemini) 서비스 추상 인터페이스
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

from ..schemas import ChatResponse


class BaseLLMApiInterface(ABC):
    """
    response_format은 provider마다 다른 파라미터로 감싸지기 전의
    순수 JSON Schema(object) dict다. 예: {"type": "object", "properties": {...},
    "required": [...], "additionalProperties": False}
    """

    @abstractmethod
    def default_model(self) -> str: ...

    @abstractmethod
    async def chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
    ) -> ChatResponse: ...

    @abstractmethod
    async def stream_chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]: ...