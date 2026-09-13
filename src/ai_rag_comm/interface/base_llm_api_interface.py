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

    images는 [{"mime_type": "image/png", "data": "<base64>"}, ...] 형태의 순수 dict
    리스트다 — provider별 이미지 콘텐츠 블록(OpenAI image_url / Claude image+base64 /
    Gemini inline_data)으로 감싸지기 전의 중립 표현이다. 크기 제한이나 형식 검증은
    라이브러리가 하지 않는다 — 그대로 API에 보내고, provider가 거부하면 그 예외가
    그대로 올라온다(로컬 LLM이 비전을 지원하지 않을 때도 마찬가지 — 조용히 무시되지 않음).

    documents는 [{"mime_type": "application/pdf", "data": "<base64>", "name": "..."}, ...]
    형태의 순수 dict 리스트다(name은 선택). images와 규칙이 동일하다 — provider별
    문서 콘텐츠 블록(OpenAI file / Claude document / Gemini inline_data — Gemini는
    PDF도 이미지와 같은 경로로 받으므로 images와 동일하게 처리됨)으로 감싸지고,
    지원하지 않는 provider는 조용히 무시하지 않고 그 예외가 그대로 올라온다.
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
        images: Optional[list[dict]] = None,
        documents: Optional[list[dict]] = None,
    ) -> ChatResponse: ...

    @abstractmethod
    async def stream_chat(
        self, prompt: str, model: Optional[str], max_tokens: int,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        strict: bool = True,
        system: Optional[str] = None,
        images: Optional[list[dict]] = None,
        documents: Optional[list[dict]] = None,
    ) -> AsyncGenerator[str, None]: ...