"""
ai_rag_comm
RAG_Router(Gateway)가 같은 프로세스에서 import해서 쓰는 내부 통신 라이브러리.
LLM API(GPT) 호출 / Local LLM 소켓 호출 / DB 호출 3가지만 제공한다.
"""

from .core import Controller
from .services import Transport, RestChannel, SocketChannel, OpenAIService
from .database import DatabaseService
from .helpers import load_config, setup_logging, Config
from .schemas import AIProvider, ChatRequest, ChatResponse

__all__ = [
    "Controller",
    "Transport", "RestChannel", "SocketChannel", "OpenAIService",
    "DatabaseService",
    "load_config", "setup_logging", "Config",
    "AIProvider", "ChatRequest", "ChatResponse",
]
