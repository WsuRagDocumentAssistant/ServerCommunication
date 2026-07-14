"""
channel_registry.py
Spring의 @Component/@Service 어노테이션에 해당하는 커스텀 데코레이터
- @Channel(transport)로 등록해두면 Transport 값만 바꿔서 구현체를 조회할 수 있음
"""

from interfaces import BaseChannelInterface
from .transport import Transport

_channel_registry: dict[Transport, type[BaseChannelInterface]] = {}


def Channel(transport: Transport):
    """클래스를 transport별 채널 레지스트리에 등록하는 데코레이터"""
    def wrapper(cls: type[BaseChannelInterface]) -> type[BaseChannelInterface]:
        _channel_registry[transport] = cls
        return cls
    return wrapper


def get_channel_cls(transport: Transport) -> type[BaseChannelInterface]:
    cls = _channel_registry.get(transport)
    if not cls:
        raise ValueError(f"등록되지 않은 통신 방식입니다: {transport}")
    return cls
