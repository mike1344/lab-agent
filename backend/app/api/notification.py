from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["站内通知"])


@router.get("/mine")
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的通知列表，按时间倒序。"""
    items = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.id.desc())
        .all()
    )
    return Response.success(
        data=[
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "content": n.content,
                "is_read": n.is_read,
                "related_id": n.related_id,
                "create_time": n.create_time,
            }
            for n in items
        ]
    )


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """未读通知数量，顶部角标用。"""
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .count()
    )
    return Response.success(data={"count": count})


@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """标记单条通知为已读。"""
    item = db.get(Notification, notification_id)
    if not item or item.user_id != current_user.id:
        raise BusinessException(code=BizCode.NOT_FOUND, message="通知不存在")
    item.is_read = True
    db.commit()
    return Response.success(message="已标记为已读")


@router.put("/read-all")
def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """一键全部已读。"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False  # noqa: E712
    ).update({"is_read": True})
    db.commit()
    return Response.success(message="全部已读")
