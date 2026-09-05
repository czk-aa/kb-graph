"""API v1 路由汇总。"""
from fastapi import APIRouter

from app.api.v1 import auth, chat, comments, documents, graph, jobs, notifications, search, spaces

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(spaces.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)
api_router.include_router(graph.router)
api_router.include_router(comments.router)
api_router.include_router(notifications.router)
