"""应用配置（pydantic-settings）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "KB-Graph"
    debug: bool = False

    # 数据库 / 缓存
    database_url: str = "postgresql+asyncpg://kb:kb123456@localhost:5432/kb"
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # LLM（OpenAI 兼容：DeepSeek / Qwen / Ollama 等）
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    # Embedding（独立配置，DeepSeek 无 embedding API）
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024

    # 分块
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64

    # 上传
    upload_max_bytes: int = 20 * 1024 * 1024
    uploads_dir: str = "uploads"

    # 检索
    search_top_k: int = 20
    retrieve_context_k: int = 8

    # 协同持久化防抖（秒）
    collab_flush_debounce: float = 3.0

    # 本地开发/测试无 Redis 时，Celery 任务同步执行
    debug_eager_tasks: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
