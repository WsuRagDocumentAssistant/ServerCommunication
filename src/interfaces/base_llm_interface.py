"""
base_llm_interface.py
로컬 LLM 서비스 추상 인터페이스
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLMInterface(ABC):

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def send(self, payload: dict) -> str: ...

    @abstractmethod
    async def stream_send(self, payload: dict) -> AsyncGenerator[str, None]: ...