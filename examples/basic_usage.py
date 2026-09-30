"""
basic_usage.py
ai_rag_comm 라이브러리를 Gateway(RAG_Router) 프로세스에서 사용하는 예시.
FastAPI/uvicorn 서버가 아니라, Controller를 직접 init/close 하고
RestChannel/SocketChannel/DatabaseService를 코드로 직접 호출한다.
"""

import asyncio
import logging
import sys

from ai_rag_comm import (
    Controller,
    RestChannel,
    LocalLLMChannel,
    AIProvider,
    load_config,
    setup_logging,
)

logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()
    setup_logging(config.server.log_level)

    controller = Controller(config=config)
    await controller.init()

    try:
        services = controller.get_services()

        rest = RestChannel(services["llm_api_config"], AIProvider.GPT)
        response = await rest.call({"prompt": "안녕", "max_tokens": 256}, stream=False)
        logger.info(f"[GPT] {response}")

        local = LocalLLMChannel(
            services["local_llm_config"].base_url,
            services["local_llm_config"].model,
            services["local_llm_config"].headers,
            services["local_llm_config"].timeout,
        )
        response = await local.call({"prompt": "안녕"}, stream=False)
        logger.info(f"[Local LLM] {response}")

        rows = await services["db"].fetch("SELECT 1")
        logger.info(f"[DB] {rows}")

        if services["school_db"] is not None:
            version = await services["school_db"].fetchval("SELECT banner FROM v$version WHERE ROWNUM = 1")
            logger.info(f"[School Oracle] {version}")
    finally:
        await controller.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        # python-oracledb async 드라이버가 Windows 기본 Proactor 루프와 호환되지 않음
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
