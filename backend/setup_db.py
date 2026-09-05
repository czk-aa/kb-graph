"""创建 kb 数据库（如果不存在）并运行迁移。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main():
    admin_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = 'kb'")
            )
            if not exists:
                await conn.execute(text("CREATE DATABASE kb"))
                print("[ok] created database kb")
            else:
                print("[ok] database kb already exists")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())