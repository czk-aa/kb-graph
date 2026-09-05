"""空间路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, get_space_role, require_space_role
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models import Space, SpaceMember, SpaceRole, User
from app.schemas.space import (
    SpaceCreate,
    SpaceMemberAdd,
    SpaceMemberOut,
    SpaceMemberUpdate,
    SpaceOut,
    SpaceUpdate,
    UserBrief,
)

router = APIRouter(prefix="/spaces", tags=["spaces"])

AdminRequired = Depends(require_space_role("admin"))
MemberRequired = Depends(require_space_role("member"))


async def _load_space(db, space_id: int) -> Space:
    space = await db.get(Space, space_id)
    if space is None:
        raise NotFoundError("空间不存在")
    return space


async def _to_out(db, space: Space, user_id: int) -> SpaceOut:
    role = await get_space_role(db, space.id, user_id)
    out = SpaceOut.model_validate(space)
    out.my_role = role.value if role else "member"
    return out


@router.get("", response_model=list[SpaceOut])
async def list_spaces(current_user: CurrentUser, db: DbSession) -> list[SpaceOut]:
    rows = await db.scalars(
        select(Space)
        .join(SpaceMember, SpaceMember.space_id == Space.id)
        .where(SpaceMember.user_id == current_user.id)
        .order_by(Space.updated_at.desc())
    )
    return [await _to_out(db, s, current_user.id) for s in rows]


@router.post("", response_model=SpaceOut, status_code=201)
async def create_space(body: SpaceCreate, current_user: CurrentUser, db: DbSession) -> SpaceOut:
    space = Space(name=body.name, description=body.description, owner_id=current_user.id)
    space.members.append(SpaceMember(user_id=current_user.id, role=SpaceRole.owner))
    db.add(space)
    await db.commit()
    await db.refresh(space)
    return await _to_out(db, space, current_user.id)


@router.get("/{space_id}", response_model=SpaceOut)
async def get_space(
    space_id: int, current_user: CurrentUser, db: DbSession, _: User = MemberRequired
) -> SpaceOut:
    space = await _load_space(db, space_id)
    return await _to_out(db, space, current_user.id)


@router.patch("/{space_id}", response_model=SpaceOut)
async def update_space(
    space_id: int,
    body: SpaceUpdate,
    current_user: CurrentUser,
    db: DbSession,
    _: User = AdminRequired,
) -> SpaceOut:
    space = await _load_space(db, space_id)
    if body.name is not None:
        space.name = body.name
    if body.description is not None:
        space.description = body.description
    await db.commit()
    await db.refresh(space)
    return await _to_out(db, space, current_user.id)


@router.delete("/{space_id}", status_code=204)
async def delete_space(
    space_id: int, current_user: CurrentUser, db: DbSession
) -> None:
    space = await _load_space(db, space_id)
    if space.owner_id != current_user.id:
        raise PermissionDeniedError("仅空间所有者可删除空间")
    await db.delete(space)
    await db.commit()


@router.get("/{space_id}/members", response_model=list[SpaceMemberOut])
async def list_members(
    space_id: int, current_user: CurrentUser, db: DbSession, _: User = MemberRequired
) -> list[SpaceMemberOut]:
    await _load_space(db, space_id)
    rows = await db.scalars(
        select(SpaceMember).where(SpaceMember.space_id == space_id).order_by(SpaceMember.created_at)
    )
    members: list[SpaceMemberOut] = []
    for m in rows:
        user = await db.get(User, m.user_id)
        members.append(
            SpaceMemberOut(user=UserBrief.model_validate(user), role=m.role.value, created_at=m.created_at)
        )
    return members


@router.post("/{space_id}/members", response_model=SpaceMemberOut, status_code=201)
async def add_member(
    space_id: int,
    body: SpaceMemberAdd,
    current_user: CurrentUser,
    db: DbSession,
    _: User = AdminRequired,
) -> SpaceMemberOut:
    space = await _load_space(db, space_id)
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None:
        raise NotFoundError("用户不存在")
    exists = await get_space_role(db, space_id, user.id)
    if exists:
        raise ConflictError("已是空间成员")
    member = SpaceMember(space_id=space.id, user_id=user.id, role=SpaceRole(body.role))
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return SpaceMemberOut(user=UserBrief.model_validate(user), role=body.role, created_at=member.created_at)


@router.patch("/{space_id}/members/{user_id}", response_model=SpaceMemberOut)
async def update_member(
    space_id: int,
    user_id: int,
    body: SpaceMemberUpdate,
    current_user: CurrentUser,
    db: DbSession,
    _: User = AdminRequired,
) -> SpaceMemberOut:
    await _load_space(db, space_id)
    member = await db.scalar(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == user_id
        )
    )
    if member is None:
        raise NotFoundError("成员不存在")
    if member.role == SpaceRole.owner:
        raise PermissionDeniedError("不能修改所有者角色")
    member.role = SpaceRole(body.role)
    await db.commit()
    user = await db.get(User, user_id)
    return SpaceMemberOut(user=UserBrief.model_validate(user), role=body.role, created_at=member.created_at)


@router.delete("/{space_id}/members/{user_id}", status_code=204)
async def remove_member(
    space_id: int, user_id: int, current_user: CurrentUser, db: DbSession, _: User = AdminRequired
) -> None:
    space = await _load_space(db, space_id)
    if user_id == space.owner_id:
        raise PermissionDeniedError("不能移除所有者")
    member = await db.scalar(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == user_id
        )
    )
    if member is None:
        raise NotFoundError("成员不存在")
    await db.delete(member)
    await db.commit()
