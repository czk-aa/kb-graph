"""Celery 应用配置。本地无 Redis 时设置 DEBUG_EAGER_TASKS=true 同步执行。"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

app = Celery(
    "kb_graph",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.parse_task"],
)
app.conf.update(
    task_always_eager=settings.debug_eager_tasks,
    task_eager_propagates=False,
    timezone="UTC",
    worker_concurrency=4,
)
if settings.debug_eager_tasks:
    # eager 模式不连接 broker/result store
    app.conf.update(task_ignore_result=True, result_backend=None, broker_url=None)
