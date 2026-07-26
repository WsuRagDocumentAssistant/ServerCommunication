"""
server_starter.py
서버 진입점
"""

import asyncio
import logging
import signal

import uvicorn

from core import Controller, create_app
from utils import load_config, setup_logging

logger = logging.getLogger(__name__)


async def run_server() -> None:
    config = load_config()
    setup_logging(config.server.log_level)

    controller = Controller(config=config)
    app = create_app(controller=controller)

    uv_config = uvicorn.Config(
        app=app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level.lower(),
        loop="asyncio",
        ws="websockets",
        log_config=None,
    )
    server = uvicorn.Server(uv_config)

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


if __name__ == "__main__":
    asyncio.run(run_server())