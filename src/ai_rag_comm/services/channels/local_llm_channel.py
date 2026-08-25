"""
local_llm_channel.py
사내 로컬 LLM 채널
- KServe로 서빙되는 OpenAI 호환 HTTP 엔드포인트 (예: http://117.16.166.22/v1)
- LLM API(GPT) 선택기(RestChannel/AIProvider)와는 별개의 채널이다.
  인증 방식이 API 키가 아니라 커스텀 헤더(예: x-user-id)라 같은 레지스트리로 묶지 않는다.
"""

from typing import AsyncGenerator, Optional, Union

from ...interface import BaseChannelInterface
from ..llm_api import OpenAIService


class LocalLLMChannel(BaseChannelInterface):
    def __init__(
        self,
        base_url: str,
        model: str,
        headers: Optional[dict] = None,
        timeout: Optional[float] = None,
    ):
        # AsyncOpenAI는 api_key가 없으면 생성 자체를 거부한다. 로컬 엔드포인트는 이 값을
        # 쓰지 않지만, Authorization: Bearer <값> 헤더로 그대로 전송되니 문제가 되면
        # 게이트웨이 쪽에서 해당 헤더를 무시하도록 맞춰야 한다.
        self._client = OpenAIService(
            api_key="not-needed",
            default_model=model,
            base_url=base_url,
            default_headers=headers,
            timeout=timeout,
        )

    async def call(self, payload: dict, *, stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        prompt = payload["prompt"]
        model = payload.get("model")
        max_tokens = payload.get("max_tokens", 1024)
        temperature = payload.get("temperature")
        response_format = payload.get("response_format")

        if stream:
            return self._client.stream_chat(prompt, model, max_tokens, temperature, response_format)

        response = await self._client.chat(prompt, model, max_tokens, temperature, response_format)
        return response.content
