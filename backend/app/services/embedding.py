"""Embedding 客户端：OpenAI 兼容 API。"""
from openai import AsyncOpenAI

from app.core.config import get_settings


class OpenAIEmbeddingClient:
    """与 LLM 分离的独立配置（DeepSeek 无 embedding API，可用 Qwen/Ollama bge-m3）。"""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            base_url=settings.embedding_base_url or None,
            api_key=settings.embedding_api_key or "not-needed",
        )
        self._model = settings.embedding_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]

    async def embed_query(self, text: str) -> list[float]:
        (vec,) = await self.embed_texts([text])
        return vec


class FakeEmbeddingClient:
    """确定性哈希向量，用于测试（可按关键词偏置相似度）。"""

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or get_settings().embedding_dim

    def _vec(self, text: str) -> list[float]:
        import hashlib
        import struct

        out: list[float] = []
        seed = 0
        # 分桶哈希：相同 token 落同一维度，产生可控的相似性
        buckets = [0.0] * self.dim
        for token in text.lower().split() or [text]:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            idx = struct.unpack("<I", digest[:4])[0] % self.dim
            sign = 1.0 if digest[4] % 2 else -1.0
            buckets[idx] += sign
            seed ^= idx
        norm = sum(b * b for b in buckets) ** 0.5 or 1.0
        out = [b / norm for b in buckets]
        return out

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vec(text)
