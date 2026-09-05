"""FastAPI 依赖：认证与空间权限。"""
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, NotFoundError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import SpaceMember, SpaceRole, User
from app.models.space import ROLE_ORDER

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: DbSession) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AuthError()
    user_id = decode_access_token(auth.removeprefix("Bearer ").strip())
    if user_id is None:
        raise AuthError()
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_space_role(db: AsyncSession, space_id: int, user_id: int) -> SpaceRole | None:
    """查询用户在空间中的角色；非成员返回 None。"""
    membership = await db.scalar(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == user_id
        )
    )
    return membership.role if membership else None


def require_space_role(min_role: str = "member"):
    """依赖工厂：要求当前用户在路径 space_id 空间中至少具备 min_role 角色。"""

    async def _dependency(space_id: int, current_user: CurrentUser, db: DbSession) -> User:
        role = await get_space_role(db, space_id, current_user.id)
        if role is None:
            # 区分 403/404：非成员一律 403，不暴露空间存在性
            raise PermissionDeniedError()
        if ROLE_ORDER[role.value] < ROLE_ORDER[min_role]:
            raise PermissionDeniedError()
        return current_user

    return _dependency
