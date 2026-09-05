"""通知路由。"""
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, update

from app.core.deps import CurrentUser, DbSession
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: int
    space_id: int
    type: str
    title: str
    body: str
    ref_id: int | None
    is_read: bool
    created_at: object

    class Config:
        from_attributes = True


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    unread_only: bool = False,
    limit: int = 50,
):
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)  # noqa: E712
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    rows = (await db.scalars(stmt)).all()
    return list(rows)


@router.post("/read-all", status_code=204)
async def mark_all_read(current_user: CurrentUser, db: DbSession) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(notification_id: int, current_user: CurrentUser, db: DbSession) -> None:
    notif = await db.get(Notification, notification_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        await db.commit()