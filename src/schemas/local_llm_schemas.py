"""
local_llm_schemas.py
로컬 LLM 소켓 요청/응답 스키마
"""

from typing import Optional

from pydantic import BaseModel


class LocalLLMRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7
    stream: bool = False


class LocalLLMResponse(BaseModel):
    content: str
    tokens_used: Optional[int] = None