"""
socket_channel.py
로컬 LLM TCP 소켓 채널
- 소켓 연결/전송 로직(예전 local_llm_service.py)을 여기로 흡수함
- 요청마다 TCP 연결을 열고 닫는 무상태(stateless) 방식
"""

import asyncio
import json
from typing import AsyncGenerator, Union

from ...interface import BaseChannelInterface


class SocketChannel(BaseChannelInterface):
    def __init__(self, host: str, port: int, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    async def call(self, payload: dict, *, stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        if stream:
            return self._stream_send(payload)
        return await self._send(payload)

    async def _send(self, payload: dict) -> str:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=self.timeout,
        )
        try:
            data = json.dumps(payload, ensure_ascii=False) + "\n"
            writer.write(data.encode("utf-8"))
            await writer.drain()

            chunks = []
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
                if not line:
                    break
                decoded = line.decode("utf-8").strip()
                if decoded == "<|END|>":
                    break
                chunks.append(decoded)
            return "".join(chunks)
        finally:
            writer.close()
            await writer.wait_closed()

    async def _stream_send(self, payload: dict) -> AsyncGenerator[str, None]:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=self.timeout,
        )
        try:
            payload["stream"] = True
            data = json.dumps(payload, ensure_ascii=False) + "\n"
            writer.write(data.encode("utf-8"))
            await writer.drain()

            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
                if not line:
                    break
                decoded = line.decode("utf-8").strip()
                if decoded == "<|END|>":
                    break
                yield decoded
        finally:
            writer.close()
            await writer.wait_closed()
