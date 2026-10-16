from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.announcement import Announcement
from app.models.user import User
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate

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


def announcement_query(db: Session):
    return db.query(Announcement).options(joinedload(Announcement.publisher))


@router.get("")
def get_announcement_list(
    keyword: str = "",
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """所有登录用户查看公告列表；置顶公告优先，其余按发布时间倒序。"""
    query = announcement_query(db)
    if keyword.strip():
        query = query.filter(Announcement.title.like(f"%{keyword.strip()}%"))
    items = query.order_by(Announcement.is_pinned.desc(), Announcement.id.desc()).all()
    return Response.success(data=[announcement_to_dict(item) for item in items])


@router.get("/{announcement_id}")
def get_announcement_detail(
    announcement_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = announcement_query(db).filter(Announcement.id == announcement_id).first()
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    return Response.success(data=announcement_to_dict(item))


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
    db: Session = Depends(get_db),
):
    item = db.get(Announcement, announcement_id)
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="公告不存在")
    db.delete(item)
    db.commit()
    return Response.success(message="公告删除成功")
