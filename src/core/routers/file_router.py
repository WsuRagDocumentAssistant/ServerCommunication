"""
file_router.py
hwpx 파일 업로드 라우터
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from utils.response_helper import ok

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/home/jovyan/rag/uploads")


class FileRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/file", tags=["File"])
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self._setup_routes()

    def _setup_routes(self):
        self.router.post("/upload")(self._upload)

    async def _upload(self, file: UploadFile = File(...)):
        if not file.filename.endswith(".hwpx"):
            raise HTTPException(status_code=400, detail="hwpx 파일만 업로드 가능합니다.")

        save_path = UPLOAD_DIR / file.filename

        content = await file.read()
        save_path.write_bytes(content)

        logger.info(f"[FileRouter] 파일 저장 완료: {save_path}")

        # TODO: 후처리 로직 연결

        return ok(data={"filename": file.filename, "path": str(save_path), "size": len(content)})
