"""
base_channel_interface.py
통신 방식(Transport)과 무관하게 동일한 방식으로 호출할 수 있는 채널 추상 인터페이스
- stream=False → 값 하나 반환
- stream=True  → AsyncGenerator 반환 (호출부에서 순회)
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Union


class BaseChannelInterface(ABC):

    @abstractmethod
    async def call(self, payload: dict, *, stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        ...
