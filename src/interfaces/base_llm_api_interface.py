"""
base_llm_api_interface.py
외부 LLM API(Claude/GPT/Gemini) 서비스 추상 인터페이스
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

from schemas import ChatResponse


class BaseLLMApiInterface(ABC):

    @abstractmethod
    def default_model(self) -> str: ...

    @abstractmethod
    async def chat(self, prompt: str, model: Optional[str], max_tokens: int) -> ChatResponse: ...

    @abstractmethod
    async def stream_chat(self, prompt: str, model: Optional[str], max_tokens: int) -> AsyncGenerator[str, None]: ...