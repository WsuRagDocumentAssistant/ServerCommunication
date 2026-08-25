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
    (OpenAI 봉투 {"type": "json_schema", "json_schema": {...}}를 그대로 넣지 말 것 —
    스키마의 type이 "json_schema"가 되어 provider마다 400으로 거부된다.)

    strict는 OpenAI 계열(GPT/로컬 LLM)에서만 의미가 있다. True면 선택 필드가 있는
    스키마도 400으로 거부되니(모든 속성이 required + additionalProperties: false 강제),
    선택 필드가 필요하면 False로 넘긴다. Claude/Gemini는 이 값을 무시한다.
    """

    @abstractmethod
    def default_model(self) -> str: ...

    @abstractmethod
    async def chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
    ) -> ChatResponse: ...

    @abstractmethod
    async def stream_chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
    ) -> AsyncGenerator[str, None]: ...