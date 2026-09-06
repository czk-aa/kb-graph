"""客户端注册表：LLM / Embedding 可在测试中替换为 Fake。

任务（Celery）上下文无法访问 app.state，故用模块级单例。
"""
from collections.abc import AsyncIterator
from typing import Any, Protocol


class EmbeddingClient(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class LLMClient(Protocol):
    def chat_stream(
        self, messages: list[dict], temperature: float = 0.3
    ) -> AsyncIterator[str]: ...

    async def chat_json(self, system: str, user: str) -> dict[str, Any]: ...


_embedding: EmbeddingClient | None = None
_llm: LLMClient | None = None


def get_embedding_client() -> EmbeddingClient:
    global _embedding
    if _embedding is None:
        from app.core.config import get_settings
        from app.services.embedding import FakeEmbeddingClient, OpenAIEmbeddingClient

        settings = get_settings()
        if settings.embedding_base_url:
            _embedding = OpenAIEmbeddingClient()
        else:
            _embedding = FakeEmbeddingClient()
    return _embedding


def set_embedding_client(client: EmbeddingClient | None) -> None:
    global _embedding
    _embedding = client


def get_llm_client() -> LLMClient:
    global _llm
    if _llm is None:
        from app.services.llm import OpenAILLMClient

        _llm = OpenAILLMClient()
    return _llm


def set_llm_client(client: LLMClient | None) -> None:
    global _llm
    _llm = client
