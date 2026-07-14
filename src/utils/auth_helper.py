"""
auth_helper.py
자체 발급 액세스 토큰(JWT) 검증 FastAPI Depends
"""

import logging

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services import ServiceOp, get_service_cls

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials if credentials else ""

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    services = request.app.state.services
    decode_token = get_service_cls(ServiceOp.AUTH_DECODE_TOKEN)(**services)

    try:
        return await decode_token.call({"token": token})
    except ValueError:
        raise HTTPException(status_code=401, detail="Unauthorized")
