"""
transport.py
통신 방식 종류
- 지금 실제로 쓰는 건 REST(외부 LLM API), SOCKET(로컬 LLM)뿐이라 이 둘만 구현체가 있음
- SSE/WEBSOCKET은 필요해질 때 여기에 값만 추가하고 채널 구현체를 만들면 됨
"""

from enum import Enum


class Transport(str, Enum):
    REST = "rest"
    SOCKET = "socket"
    SSE = "sse"
    WEBSOCKET = "websocket"
