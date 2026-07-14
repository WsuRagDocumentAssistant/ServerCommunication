"""
route_registry.py
Spring의 @GetMapping/@PostMapping에 해당하는 커스텀 어노테이션
- @Route(method, path)로 등록해두면 build_router()가 한 번에 FastAPI에 붙여준다
"""

from interfaces import BaseRouteInterface

_route_registry: dict[tuple, tuple] = {}  # (method, path) -> (cls, tags)


def Route(method: str, path: str, tags: list = None):
    """클래스를 (method, path)로 라우트 레지스트리에 등록하는 데코레이터"""
    def wrapper(cls: type[BaseRouteInterface]) -> type[BaseRouteInterface]:
        _route_registry[(method.upper(), path)] = (cls, tags or [])
        return cls
    return wrapper


def get_registered_routes() -> dict[tuple, tuple]:
    return dict(_route_registry)
