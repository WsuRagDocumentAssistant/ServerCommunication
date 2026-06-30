"""
auth.py
SSO 토큰 검증 FastAPI Depends
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
    user_service = request.app.state.user_service
    token = credentials.credentials if credentials else ""

    if not await user_service.validate_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await user_service.get_user_info(token)
