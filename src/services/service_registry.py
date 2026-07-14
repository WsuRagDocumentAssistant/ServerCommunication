"""
service_registry.py
Spring의 @Service 어노테이션에 해당하는 커스텀 데코레이터 (channel_registry.py와 동일 구조)
- @Service(op)로 등록해두면 ServiceOp 값만 바꿔서 구현체를 조회할 수 있음
"""

from interfaces import BaseServiceInterface
from .ops import ServiceOp

_service_registry: dict[ServiceOp, type[BaseServiceInterface]] = {}


def Service(op: ServiceOp):
    """클래스를 ServiceOp별 레지스트리에 등록하는 데코레이터"""
    def wrapper(cls: type[BaseServiceInterface]) -> type[BaseServiceInterface]:
        _service_registry[op] = cls
        return cls
    return wrapper


def get_service_cls(op: ServiceOp) -> type[BaseServiceInterface]:
    cls = _service_registry.get(op)
    if not cls:
        raise ValueError(f"등록되지 않은 서비스 명령입니다: {op}")
    return cls
