"""Yjs 协同编辑 WebSocket 服务端。

基于 pycrdt.websocket 实现 CRDT 实时同步。
"""
from __future__ import annotations

import asyncio
from typing import Any

from pycrdt.websocket import ASGIServer, WebsocketServer
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.session import get_session_factory
from app.models.document import Document


def create_collab_server() -> ASGIServer:
    """创建 Yjs 协同编辑 ASGI 服务。"""

    ws_server = WebsocketServer(rooms_ready=False, auto_clean_rooms=True)

    async def on_connect(_msg: dict, scope: dict) -> bool:
        """WebSocket 连接鉴权：校验 JWT + 空间权限。返回 True 表示拒绝连接。"""
        # 从 query string 提取 token
        qs = scope.get("query_string", b"").decode()
        token = None
        for pair in qs.split("&"):
            if pair.startswith("token="):
                token = pair[6:]
                break

        if not token:
            return True

        user_id = decode_access_token(token)
        if user_id is None:
            return True

        # 从路径提取 document_id
        path = scope.get("path", "")
        parts = path.strip("/").split("/")
        if len(parts) < 3 or not parts[-1].isdigit():
            return True

        doc_id = int(parts[-1])

        # 验证文档存在且用户有权限
        factory = get_session_factory()
        async with factory() as s:
            doc = await s.get(Document, doc_id)
            if doc is None:
                return True
            from app.models.space import SpaceMember
            member = await s.scalar(
                select(SpaceMember).where(
                    SpaceMember.space_id == doc.space_id,
                    SpaceMember.user_id == user_id,
                )
            )
            if not member:
                return True

        # 鉴权通过
        scope["user_id"] = user_id
        scope["document_id"] = doc_id
        return False

    return ASGIServer(websocket_server=ws_server, on_connect=on_connect)