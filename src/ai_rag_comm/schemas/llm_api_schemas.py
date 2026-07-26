"""
llm_api_schemas.py
외부 LLM API(GPT) 요청/응답 스키마
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AIProvider(str, Enum):
    GPT = "gpt"


class ChatRequest(BaseModel):
    provider: AIProvider = AIProvider.GPT
    model: Optional[str] = None
    prompt: str
    max_tokens: int = 1024
    stream: bool = False


class ChatResponse(BaseModel):
    provider: str
    model: str
    content: str
