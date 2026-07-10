"""
llm_api_schemas.py
외부 LLM API(Claude/GPT/Gemini) 요청/응답 스키마
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AIProvider(str, Enum):
    CLAUDE = "claude"
    GPT = "gpt"
    GEMINI = "gemini"


class ChatRequest(BaseModel):
    provider: AIProvider = AIProvider.CLAUDE
    model: Optional[str] = None
    prompt: str
    max_tokens: int = 1024
    stream: bool = False


class ChatResponse(BaseModel):
    provider: str
    model: str
    content: str