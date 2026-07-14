"""
file_upload_route.py
hwpx 파일 업로드 라우트
"""

import logging
from pathlib import Path

from fastapi import HTTPException

from interfaces import BaseRouteInterface
from utils.response_helper import ok
from .route_registry import Route

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/home/jovyan/rag/uploads")


@Route("POST", "/file/upload", tags=["File"])
class FileUploadRoute(BaseRouteInterface):
    def __init__(self, **services):
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async def call(self, payload: dict) -> dict:
        file = payload.get("file")
        if file is None or not hasattr(file, "filename"):
            raise HTTPException(status_code=400, detail="file 필드가 필요합니다.")

        if not file.filename.endswith(".hwpx"):
            raise HTTPException(status_code=400, detail="hwpx 파일만 업로드 가능합니다.")

        save_path = UPLOAD_DIR / file.filename
        content = await file.read()
        save_path.write_bytes(content)

        logger.info(f"[FileUploadRoute] 파일 저장 완료: {save_path}")

        # TODO: 후처리 로직 연결

        return ok(data={"filename": file.filename, "path": str(save_path), "size": len(content)})
