"""
auth_helper.py
자체 발급 액세스 토큰(JWT) 검증 FastAPI Depends
"""

import logging

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    auth_service = request.app.state.auth_service
    token = credentials.credentials if credentials else ""

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        return auth_service.decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Unauthorized")
