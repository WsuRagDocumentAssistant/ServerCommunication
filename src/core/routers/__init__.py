from .route_registry import Route, get_registered_routes
from .route_dispatcher import build_router

# 아래 임포트들은 각 파일의 @Route 데코레이터를 실행시켜 레지스트리에 등록하기 위함 (직접 사용 안 해도 필요)
from . import health_route  # noqa: F401
from . import file_upload_route  # noqa: F401
from . import auth_routes  # noqa: F401

__all__ = ["Route", "get_registered_routes", "build_router"]
