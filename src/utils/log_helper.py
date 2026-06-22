"""
log_helper.py
로깅 설정 헬퍼
- setup_logging()은 server_starter.py에서 1회만 호출
- 각 모듈은 import logging + logging.getLogger(__name__) 사용
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """server_starter.py에서 1회만 호출"""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)
        uv_logger.setLevel(numeric_level)
        uv_logger.propagate = False