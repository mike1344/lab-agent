from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.dependencies.signature import require_signature
from app.models.announcement import Announcement
from app.models.announcement_comment import AnnouncementComment
from app.models.announcement_read import AnnouncementRead
from app.models.user import User
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from app.schemas.announcement_comment import CommentCreate

router = APIRouter(prefix="/announcements", tags=["系统公告"])


def announcement_to_dict(item: Announcement) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "content": item.content,
        "is_pinned": item.is_pinned,
        "publisher_id": item.publisher_id,
        "publisher_name": item.publisher.full_name or item.publisher.username,
        "create_time": item.create_time,
        "update_time": item.update_time,
    }


def comment_to_dict(comment: AnnouncementComment) -> dict:
    return {
        "id": comment.id,
        "announcement_id": comment.announcement_id,
        "user_id": comment.user_id,
        "username": comment.user.full_name or comment.user.username,
        "avatar_url": comment.user.avatar_url,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "create_time": comment.create_time,
    }


def announcement_query(db: Session):
    return db.query(Announcement).options(joinedload(Announcement.publisher))


def _attach_read_state(rows: list[dict], db: Session, user_id: int) -> list[dict]:
    """一次查出当前用户读过的公告与每条公告的已读人数，避免列表接口 N+1 查询。"""
    announcement_ids = [row["id"] for row in rows]
    if not announcement_ids:
        return rows
    read_ids = {
        row[0]
        for row in db.query(AnnouncementRead.announcement_id)
        .filter(
            AnnouncementRead.user_id == user_id,
            AnnouncementRead.announcement_id.in_(announcement_ids),
        )
        .all()
    }
    read_counts = dict(
        db.query(AnnouncementRead.announcement_id, func.count(AnnouncementRead.id))
        .filter(AnnouncementRead.announcement_id.in_(announcement_ids))
        .group_by(AnnouncementRead.announcement_id)
        .all()
    )
    for row in rows:
        row["is_read"] = row["id"] in read_ids
        row["read_count"] = read_counts.get(row["id"], 0)
    return rows


@router.get("")
def get_announcement_list(
    keyword: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """所有登录用户查看公告列表；置顶公告优先，其余按发布时间倒序。"""
    query = announcement_query(db)
    if keyword.strip():
        query = query.filter(Announcement.title.like(f"%{keyword.strip()}%"))
    items = query.order_by(Announcement.is_pinned.desc(), Announcement.id.desc()).all()
    rows = _attach_read_state([announcement_to_dict(item) for item in items], db, current_user.id)
    return Response.success(data=rows)


@router.get("/{announcement_id}")
def get_announcement_detail(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = announcement_query(db).filter(Announcement.id == announcement_id).first()
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    row = _attach_read_state([announcement_to_dict(item)], db, current_user.id)[0]
    return Response.success(data=row)


@router.post("")
def create_announcement(
    data: AnnouncementCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员发布公告。"""
    item = Announcement(publisher_id=current_user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    item = announcement_query(db).filter(Announcement.id == item.id).first()
    return Response.success(message="公告发布成功", data=announcement_to_dict(item))


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.get(Announcement, announcement_id)
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    item = announcement_query(db).filter(Announcement.id == item.id).first()
    return Response.success(message="公告修改成功", data=announcement_to_dict(item))


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    _: User = Depends(get_current_admin),
    _sig: User = Depends(require_signature),
    db: Session = Depends(get_db),
):
    item = db.get(Announcement, announcement_id)
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    # 连带清理评论与已读回执，避免留下孤儿数据（无外键级联删除时由应用层保证）。
    db.query(AnnouncementComment).filter(AnnouncementComment.announcement_id == announcement_id).delete(
        synchronize_session=False
    )
    db.query(AnnouncementRead).filter(AnnouncementRead.announcement_id == announcement_id).delete(
        synchronize_session=False
    )
    db.delete(item)
    db.commit()
    return Response.success(message="公告删除成功")


@router.post("/{announcement_id}/read")
def mark_announcement_read(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """标记公告已读（幂等）：重复调用只保留首次回执。"""
    if not db.get(Announcement, announcement_id):
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    exists = (
        db.query(AnnouncementRead)
        .filter(
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.user_id == current_user.id,
        )
        .first()
    )
    if not exists:
        db.add(AnnouncementRead(announcement_id=announcement_id, user_id=current_user.id))
        db.commit()
    read_count = db.query(AnnouncementRead).filter(AnnouncementRead.announcement_id == announcement_id).count()
    return Response.success(message="已读", data={"read_count": read_count})


@router.get("/{announcement_id}/read-receipts")
def get_read_receipts(
    announcement_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员查看已读回执：已读人数 / 在册人数 + 已读名单（含首次阅读时间）。"""
    if not db.get(Announcement, announcement_id):
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    reads = (
        db.query(AnnouncementRead)
        .options(joinedload(AnnouncementRead.user))
        .filter(AnnouncementRead.announcement_id == announcement_id)
        .order_by(AnnouncementRead.id.desc())
        .all()
    )
    total_users = db.query(User).filter(User.is_active.is_(True)).count()
    return Response.success(
        data={
            "read_count": len(reads),
            "total_users": total_users,
            "readers": [
                {
                    "user_id": read.user_id,
                    "username": read.user.full_name or read.user.username,
                    "read_time": read.create_time,
                }
                for read in reads
            ],
        }
    )


@router.get("/{announcement_id}/comments")
def get_announcement_comments(
    announcement_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """公告评论列表：按时间正序返回，前端按 parent_id 组装一级回复树。"""
    if not db.get(Announcement, announcement_id):
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    comments = (
        db.query(AnnouncementComment)
        .options(joinedload(AnnouncementComment.user))
        .filter(AnnouncementComment.announcement_id == announcement_id)
        .order_by(AnnouncementComment.id.asc())
        .all()
    )
    return Response.success(data=[comment_to_dict(comment) for comment in comments])


@router.post("/{announcement_id}/comments")
def create_announcement_comment(
    announcement_id: int,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发表评论或回复（回复只允许挂在一级评论下，避免无限嵌套）。"""
    if not db.get(Announcement, announcement_id):
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    if data.parent_id is not None:
        parent = db.get(AnnouncementComment, data.parent_id)
        if not parent or parent.announcement_id != announcement_id:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="回复的评论不存在或不属于该公告")
        if parent.parent_id is not None:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="仅支持回复一级评论")
    comment = AnnouncementComment(
        announcement_id=announcement_id,
        user_id=current_user.id,
        parent_id=data.parent_id,
        content=data.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment = (
        db.query(AnnouncementComment)
        .options(joinedload(AnnouncementComment.user))
        .filter(AnnouncementComment.id == comment.id)
        .first()
    )
    return Response.success(message="评论成功", data=comment_to_dict(comment))


@router.delete("/comments/{comment_id}")
def delete_announcement_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除评论：作者本人或管理员；删除一级评论时连带删除其回复。"""
    comment = db.get(AnnouncementComment, comment_id)
    if not comment:
        raise BusinessException(code=BizCode.NOT_FOUND, message="评论不存在")
    if comment.user_id != current_user.id and not current_user.is_superuser:
        raise BusinessException(code=BizCode.FORBIDDEN, message="只能删除自己的评论")
    db.query(AnnouncementComment).filter(AnnouncementComment.parent_id == comment_id).delete(synchronize_session=False)
    db.delete(comment)
    db.commit()
    return Response.success(message="评论删除成功")
