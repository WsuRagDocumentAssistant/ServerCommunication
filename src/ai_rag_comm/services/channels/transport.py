"""
transport.py
통신 방식 종류
- LLM API(GPT)는 REST, 로컬 LLM은 SOCKET으로만 통신한다
"""

from enum import Enum


class Transport(str, Enum):
    REST = "rest"
    SOCKET = "socket"
