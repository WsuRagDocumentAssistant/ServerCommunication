"""
local_llm_service.py
로컬 LLM 소켓 서비스
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from interfaces import BaseLocalLLMInterface

logger = logging.getLogger(__name__)


class LocalLLMService(BaseLocalLLMInterface):
    def __init__(self, host: str, port: int, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.is_connected = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            self.is_connected = True
            logger.info(f"[LLM] 연결 성공: {self.host}:{self.port}")
        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            self.is_connected = False
            logger.warning(f"[LLM] 연결 실패: {e}")
            raise

    async def disconnect(self) -> None:
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self.is_connected = False
        logger.info("[LLM] 연결 해제")

    async def _ensure_connected(self) -> None:
        if not self.is_connected:
            await self.connect()

    async def send(self, payload: dict) -> str:
        async with self._lock:
            await self._ensure_connected()
            data = json.dumps(payload, ensure_ascii=False) + "\n"
            self._writer.write(data.encode("utf-8"))
            await self._writer.drain()
            chunks = []
            while True:
                try:
                    line = await asyncio.wait_for(self._reader.readline(), timeout=self.timeout)
                    if not line:
                        break
                    decoded = line.decode("utf-8").strip()
                    if decoded == "<|END|>":
                        break
                    chunks.append(decoded)
                except asyncio.TimeoutError:
                    logger.error("[LLM] 응답 타임아웃")
                    self.is_connected = False
                    raise
            return "".join(chunks)

    async def stream_send(self, payload: dict) -> AsyncGenerator[str, None]:
        async with self._lock:
            await self._ensure_connected()
            payload["stream"] = True
            data = json.dumps(payload, ensure_ascii=False) + "\n"
            self._writer.write(data.encode("utf-8"))
            await self._writer.drain()
        while True:
            try:
                line = await asyncio.wait_for(self._reader.readline(), timeout=self.timeout)
                if not line:
                    break
                decoded = line.decode("utf-8").strip()
                if decoded == "<|END|>":
                    break
                yield decoded
            except asyncio.TimeoutError:
                self.is_connected = False
                raise