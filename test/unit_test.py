"""
unit_test.py

실행 (src 디렉토리에서):
    pytest ../test/unit_test.py -v --asyncio-mode=auto
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from schemas import AIProvider, ChatResponse
from services import AIService, LLMService, UserService
from interfaces import BaseAIService
from database import DatabaseService
from core import Settings, Controller, create_app
from core.routers import AIRouter, LLMRouter, ConnectionManager, ws_manager
from utils.response_helper import ok, fail


# ─────────────────────────────────────────────
# Mock 구현체
# ─────────────────────────────────────────────
class MockDB:
    def __init__(self):
        self.is_connected = True

    async def health_check(self) -> dict:
        return {"healthy": True, "connected": True}


class MockAIClient(BaseAIService):
    def default_model(self) -> str: return "mock-model"

    async def chat(self, prompt, model, max_tokens) -> ChatResponse:
        return ChatResponse(provider="mock", model="mock-model", content=f"Mock response: {prompt}")

    async def stream_chat(self, prompt, model, max_tokens):
        for word in ["Hello", " ", "World"]:
            yield word


# ─────────────────────────────────────────────
# 픽스처
# ─────────────────────────────────────────────
@pytest.fixture
def settings() -> Settings:
    return Settings(
        host="127.0.0.1", port=8001, log_level="info",
        claude_api_key="test", openai_api_key="test", gemini_api_key="test",
        llm_host="127.0.0.1", llm_port=9999, llm_timeout=30.0, llm_auto_connect=False,
        db_host="127.0.0.1", db_port=5432,
        db_user="test", db_password="test", db_name="test_db",
        db_pool_min=1, db_pool_max=2, db_auto_connect=False,
        sso_issuer_url="", sso_client_id="", sso_client_secret="",
    )

@pytest.fixture
def mock_db(): return MockDB()

@pytest.fixture
def mock_ai_service():
    svc = MagicMock(spec=AIService)
    svc.get.return_value = MockAIClient()
    return svc

@pytest.fixture
def mock_llm_service():
    svc = MagicMock(spec=LLMService)
    svc.is_connected = True
    svc.host = "127.0.0.1"
    svc.port = 9999
    svc.send = AsyncMock(return_value="LLM response text")
    return svc

@pytest.fixture
def controller(settings): return Controller(settings=settings)

@pytest.fixture
def app(controller, mock_db, mock_ai_service, mock_llm_service):
    from fastapi import FastAPI
    _app = FastAPI()
    _app.state.response = {"ok": ok, "fail": fail}
    _app.include_router(AIRouter(service=mock_ai_service).router)
    _app.include_router(LLMRouter(service=mock_llm_service).router)

    @_app.get("/health")
    async def health():
        db_health = await mock_db.health_check()
        return ok(data={
            "status": "ok",
            "ws_connections": ws_manager.get_connection_count(),
            "llm_connected": mock_llm_service.is_connected,
            "db": db_health,
        })

    return _app

@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ─────────────────────────────────────────────
# 1. WebSocket ConnectionManager
# ─────────────────────────────────────────────
class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        await manager.connect("c1", mock_ws)
        assert manager.get_connection_count() == 1
        await manager.disconnect("c1")
        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_send_personal(self):
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        await manager.connect("c1", mock_ws)
        await manager.send_personal("c1", "hello")
        mock_ws.send_text.assert_called_once_with("hello")

    @pytest.mark.asyncio
    async def test_broadcast(self):
        manager = ConnectionManager()
        clients = {"c1": AsyncMock(), "c2": AsyncMock()}
        for cid, ws in clients.items():
            await manager.connect(cid, ws)
        await manager.broadcast("msg")
        for ws in clients.values():
            ws.send_text.assert_called_once_with("msg")

    @pytest.mark.asyncio
    async def test_close_all(self):
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        await manager.connect("c1", mock_ws)
        await manager.close_all()
        assert manager.get_connection_count() == 0
        mock_ws.close.assert_called_once()


# ─────────────────────────────────────────────
# 2. SSO UserService
# ─────────────────────────────────────────────
class TestUserService:
    @pytest.mark.asyncio
    async def test_validate_token_dev_mode(self):
        svc = UserService(issuer_url="", client_id="", client_secret="")
        await svc.init()
        assert await svc.validate_token("any-token") is True
        assert await svc.validate_token("") is True

    @pytest.mark.asyncio
    async def test_validate_token_empty_with_issuer(self):
        svc = UserService(issuer_url="https://sso.example.com", client_id="id", client_secret="secret")
        assert await svc.validate_token("") is False


# ─────────────────────────────────────────────
# 3. AI 라우터
# ─────────────────────────────────────────────
class TestAIRouter:
    @pytest.mark.asyncio
    async def test_chat_endpoint(self, async_client):
        r = await async_client.post("/ai/chat", json={"provider": "claude", "prompt": "Hello", "max_tokens": 100})
        assert r.status_code == 200
        assert "Mock response: Hello" in r.json()["content"]

    @pytest.mark.asyncio
    async def test_list_providers(self, async_client):
        r = await async_client.get("/ai/providers")
        assert r.status_code == 200
        assert set(r.json()["data"]["providers"]) == {"claude", "gpt", "gemini"}

    @pytest.mark.asyncio
    async def test_chat_stream_endpoint(self, async_client):
        r = await async_client.post("/ai/chat/stream", json={"provider": "claude", "prompt": "test", "max_tokens": 100, "stream": True})
        assert r.status_code == 200


# ─────────────────────────────────────────────
# 4. LLM 소켓
# ─────────────────────────────────────────────
class TestLLMService:
    @pytest.mark.asyncio
    async def test_connect_success(self):
        svc = LLMService("127.0.0.1", 9999)
        mock_reader = AsyncMock(spec=asyncio.StreamReader)
        mock_writer = AsyncMock(spec=asyncio.StreamWriter)
        with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
            await svc.connect()
            assert svc.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_refused(self):
        svc = LLMService("127.0.0.1", 9999)
        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError):
            with pytest.raises(ConnectionRefusedError):
                await svc.connect()
            assert svc.is_connected is False

    @pytest.mark.asyncio
    async def test_send_message(self):
        svc = LLMService("127.0.0.1", 9999)
        mock_reader = AsyncMock(spec=asyncio.StreamReader)
        mock_writer = AsyncMock(spec=asyncio.StreamWriter)
        mock_reader.readline = AsyncMock(side_effect=[b"Hello World\n", b"<|END|>\n"])
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
            await svc.connect()
            result = await svc.send({"prompt": "test", "max_tokens": 100})
            assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_llm_infer_endpoint(self, async_client):
        r = await async_client.post("/llm/infer", json={"prompt": "Test", "max_tokens": 100})
        assert r.status_code == 200
        assert r.json()["content"] == "LLM response text"

    @pytest.mark.asyncio
    async def test_llm_status_endpoint(self, async_client):
        r = await async_client.get("/llm/status")
        assert r.status_code == 200
        assert r.json()["data"]["connected"] is True


# ─────────────────────────────────────────────
# 5. 서버 헬스체크
# ─────────────────────────────────────────────
class TestServerHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        r = await async_client.get("/health")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["status"] == "ok"
        assert "ws_connections" in data
        assert "llm_connected" in data
        assert "db" in data