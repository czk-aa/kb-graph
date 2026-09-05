"""评论路由。"""
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, require_space_role
from app.core.exceptions import AppError, NotFoundError, PermissionDeniedError
from app.models import Comment, Document
from app.models.notification import Notification, NotifyType

router = APIRouter(tags=["comments"])


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    parent_id: int | None = None
    anchor: str | None = None


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nickname: str
    avatar_url: str | None = None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    user_id: int
    parent_id: int | None
    content: str
    anchor: str | None
    created_at: object
    updated_at: object
    user: UserBrief | None = None
    replies: list["CommentOut"] = []


def _serialize_comment(c: Comment, max_depth: int = 2) -> dict:
    """序列化评论，避免 ORM 嵌套懒加载问题。"""
    result = {
        "id": c.id,
        "document_id": c.document_id,
        "user_id": c.user_id,
        "parent_id": c.parent_id,
        "content": c.content,
        "anchor": c.anchor,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "user": {
            "id": c.user.id,
            "nickname": c.user.nickname,
            "avatar_url": c.user.avatar_url,
        } if c.user else None,
        "replies": [],
    }
    if max_depth > 0 and c.replies:
        result["replies"] = [
            _serialize_comment(r, max_depth - 1) for r in c.replies
        ]
    return result


@router.get("/documents/{document_id}/comments", response_model=list[CommentOut])
async def list_comments(document_id: int, current_user: CurrentUser, db: DbSession):
    doc = await db.get(Document, document_id)
    if doc is None:
        raise NotFoundError("文档不存在")
    await require_space_role("member")(doc.space_id, current_user, db)

    rows = (
        await db.scalars(
            select(Comment)
            .options(selectinload(Comment.user), selectinload(Comment.replies).selectinload(Comment.user))
            .where(Comment.document_id == document_id, Comment.parent_id.is_(None))
            .order_by(Comment.created_at)
        )
    ).all()

    return [_serialize_comment(c, max_depth=1) for c in rows]


@router.post("/documents/{document_id}/comments", response_model=CommentOut, status_code=201)
async def create_comment(
    document_id: int, body: CommentCreate, current_user: CurrentUser, db: DbSession
):
    doc = await db.get(Document, document_id)
    if doc is None:
        raise NotFoundError("文档不存在")
    await require_space_role("member")(doc.space_id, current_user, db)

    comment = Comment(
        document_id=document_id,
        user_id=current_user.id,
        parent_id=body.parent_id,
        content=body.content,
        anchor=body.anchor,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment, ["user"])

    # 发送通知
    if body.parent_id:
        parent = await db.get(Comment, body.parent_id)
        if parent and parent.user_id != current_user.id:
            db.add(
                Notification(
                    user_id=parent.user_id,
                    space_id=doc.space_id,
                    type=NotifyType.comment_replied,
                    title=f"{current_user.nickname} 回复了你的评论",
                    body=body.content[:200],
                    ref_id=comment.id,
                )
            )
    else:
        if doc.created_by != current_user.id:
            db.add(
                Notification(
                    user_id=doc.created_by,
                    space_id=doc.space_id,
                    type=NotifyType.comment_created,
                    title=f"{current_user.nickname} 评论了文档「{doc.title}」",
                    body=body.content[:200],
                    ref_id=comment.id,
                )
            )
    await db.commit()

    return {
        "id": comment.id,
        "document_id": comment.document_id,
        "user_id": comment.user_id,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "anchor": comment.anchor,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "user": {
            "id": current_user.id,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
        },
        "replies": [],
    }


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: int, current_user: CurrentUser, db: DbSession) -> None:
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise NotFoundError("评论不存在")
    if comment.user_id != current_user.id:
        raise PermissionDeniedError("无权删除他人评论")
    await db.delete(comment)
    await db.commit()