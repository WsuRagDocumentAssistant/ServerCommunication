"""
route_dispatcher.py
route_registry에 등록된 (method, path) → 라우트 클래스를 실제 FastAPI APIRouter로 변환한다.
- 모든 요청을 공통 payload로 변환해 route.call(payload) 하나로 처리한다
- 라우트 클래스가 REQUEST_SCHEMA(Pydantic DTO)를 선언해두면, 요청 본문을 그 DTO로
  검증/변환한 뒤(Spring의 @Valid에 해당) call()에 넘긴다. 검증 실패 시 422를 반환한다.
- REQUEST_SCHEMA가 없으면(파일 업로드, 헤더만 쓰는 라우트 등) raw dict를 그대로 넘긴다
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from .route_registry import get_registered_routes


async def _extract_payload(request: Request) -> dict:
    payload: dict = {"_headers": dict(request.headers)}
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        payload.update({key: value for key, value in form.items()})
    elif content_type.startswith("application/json"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                payload.update(body)
        except Exception:
            pass

    return payload


def build_router(services: dict) -> APIRouter:
    router = APIRouter()

    for (method, path), (route_cls, tags) in get_registered_routes().items():
        route_instance = route_cls(**services)
        request_schema = getattr(route_cls, "REQUEST_SCHEMA", None)

        def make_handler(instance, req_schema):
            async def handler(request: Request):
                raw = await _extract_payload(request)

                if req_schema is not None:
                    body = {k: v for k, v in raw.items() if k != "_headers"}
                    try:
                        payload = req_schema(**body)
                    except ValidationError as e:
                        raise HTTPException(status_code=422, detail=e.errors())
                else:
                    payload = raw

                return await instance.call(payload)
            return handler

        router.add_api_route(path, make_handler(route_instance, request_schema), methods=[method], tags=tags)

    return router
