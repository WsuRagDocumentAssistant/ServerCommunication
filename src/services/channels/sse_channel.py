"""
sse_channel.py
SSE(Server-Sent Events) 엔드포인트를 BaseChannelInterface로 감싼 채널
"""

from typing import AsyncGenerator, Optional, Union

import httpx

from interfaces import BaseChannelInterface
from .transport import Transport
from .channel_registry import Channel


@Channel(Transport.SSE)
class SSEChannel(BaseChannelInterface):
    def __init__(self, url: str, headers: Optional[dict] = None, timeout: float = 30.0):
        self._url = url
        self._headers = headers or {}
        self._timeout = timeout

    async def call(self, payload: dict, *, stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        if stream:
            return self._stream(payload)

        chunks = [chunk async for chunk in self._stream(payload)]
        return "".join(chunks)

    async def _stream(self, payload: dict) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", self._url, json=payload, headers=self._headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    yield data
