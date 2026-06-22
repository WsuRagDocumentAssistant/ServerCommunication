"""
server_starter.py
서버 진입점
- Settings 로드
- setup_logging 1회 호출
- Controller 생성
- App에 Controller 주입
- Uvicorn 실행
"""

import asyncio
import logging
import signal

import uvicorn

from core import Settings, Controller, create_app
from utils import setup_logging

logger = logging.getLogger(__name__)


async def run_server(settings: Settings) -> None:
    controller = Controller(settings=settings)
    app = create_app(controller=controller)

    config = uvicorn.Config(
        app=app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        loop="asyncio",
        ws="websockets",
        log_config=None,
    )
    server = uvicorn.Server(config)

    loop = asyncio.get_running_loop()

    def _handle_signal(sig: signal.Signals) -> None:
        logger.info(f"시그널 수신: {sig.name} → graceful shutdown 시작")
        server.should_exit = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: _handle_signal(signal.Signals(s)))

    await server.serve()


def main() -> None:
    settings = Settings()
    setup_logging(settings.log_level)
    logger.info(f"서버 설정: host={settings.host}, port={settings.port}")
    asyncio.run(run_server(settings))


if __name__ == "__main__":
    main()