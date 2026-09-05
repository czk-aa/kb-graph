"""pytest 公共夹具：测试库创建 + 迁移 + 清表 + ASGI 客户端。

默认连接 localhost 的 PostgreSQL；首次运行会自动创建 kb_test 库并执行 alembic upgrade。
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/kb_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("EMBEDDING_DIM", "8")  # 测试用小维度向量
os.environ.setdefault("UPLOADS_DIR", str(BACKEND_DIR / ".test_uploads"))
os.environ.setdefault("DEBUG_EAGER_TASKS", "true")  # Celery 同步执行

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402


def _sync_url(url: str) -> str:
    return url.replace("+asyncpg", "+psycopg2") if "+asyncpg" in url else url


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """会话级：确保 kb_test 存在并执行迁移。"""
    database_url = os.environ["DATABASE_URL"]

    def _run_migrations() -> None:
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        cfg.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(cfg, "head")

    # psycopg2 不在依赖里，用 asyncpg 裸连建库
    asyncio.run(_ensure_database(database_url))
    _run_migrations()
    yield


async def _ensure_database(url: str) -> None:
    from sqlalchemy import text

    admin_url = url.rsplit("/", 1)[0] + "/postgres"
    dbname = url.rsplit("/", 1)[1].split("?")[0]
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": dbname}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables(setup_database):
    """每个测试前动态清空所有业务表（排除 alembic_version）。"""
    from sqlalchemy import text

    from app.db.session import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        tables = await conn.scalars(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        )
        names = list(tables)
        if names:
            joined = ", ".join(f'"{n}"' for n in names)
            await conn.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE"))
            await conn.commit()
    yield


@pytest.fixture(autouse=True)
async def fake_ai_clients():
    """所有测试默认使用 Fake LLM/Embedding，可预测且无网络。"""
    from app.services.embedding import FakeEmbeddingClient
    from app.services.registry import set_embedding_client, set_llm_client

    set_embedding_client(FakeEmbeddingClient(dim=8))
    set_llm_client(FakeLLMClient())
    yield
    set_embedding_client(None)
    set_llm_client(None)


class FakeLLMClient:
    """脚本化流式输出的 Fake LLM；chat_json 返回固定抽取结果。"""

    # 与 FakeEmbedding 分桶语义一致的实体/关系样例
    EXTRACTION = {
        "entities": [
            {"name": "FastAPI", "type": "technology", "description": "Python web framework", "aliases": []},
            {"name": "PostgreSQL", "type": "technology", "description": "relational database", "aliases": []},
        ],
        "relations": [
            {
                "source": "FastAPI",
                "target": "PostgreSQL",
                "relation": "uses",
                "description": "FastAPI uses PostgreSQL",
                "evidence_quote": "FastAPI uses PostgreSQL",
            }
        ],
    }

    def __init__(self, reply: str = "这是测试回答 [1]。") -> None:
        self.reply = reply

    async def chat_stream(self, messages, temperature: float = 0.3):
        for ch in self.reply:
            yield ch

    async def chat_json(self, system: str, user: str) -> dict:
        import json

        # 只有抽取类 prompt 返回图谱数据；修复重试 prompt 返回原样
        if "知识图谱构建专家" in system:
            return self.EXTRACTION
        try:
            return json.loads(user)
        except Exception:
            return self.EXTRACTION


@pytest.fixture
async def db():
    """直接可用的数据库会话（供单元级图测试等使用）。"""
    from app.db.session import get_session_factory

    async with get_session_factory()() as session:
        yield session


@pytest.fixture
async def client():
    """httpx ASGI 客户端。"""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
