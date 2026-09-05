"""LLM 客户端：OpenAI 兼容 API（chat 流式 + JSON 输出）。"""
import json
import re
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings


class OpenAILLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url or None, api_key=settings.llm_api_key or "not-needed"
        )
        self._model = settings.llm_model

    async def chat_stream(
        self, messages: list[dict], temperature: float = 0.3
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model, messages=messages, stream=True, temperature=temperature
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return _parse_json_loose(resp.choices[0].message.content or "{}")


def _parse_json_loose(raw: str) -> dict[str, Any]:
    """strip markdown 围栏后解析 JSON。"""
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    return json.loads(text)
