from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.equipment import Equipment
from app.models.favorite import Favorite
from app.models.lab import Lab
from app.models.user import User
from app.schemas.favorite import FavoriteCreate

router = APIRouter(prefix="/favorites", tags=["我的收藏"])

TARGET_MODELS = {"lab": Lab, "equipment": Equipment}


def _target_exists(db: Session, target_type: str, target_id: int) -> bool:
    model = TARGET_MODELS.get(target_type)
    return bool(model and db.get(model, target_id))


def _favorite_to_dict(db: Session, favorite: Favorite) -> dict:
    """收藏项附带目标名称，前端直接渲染；目标被删除时 available=False 并会被列表过滤。"""
    data = {
        "id": favorite.id,
        "target_type": favorite.target_type,
        "target_id": favorite.target_id,
        "name": None,
        "status": None,
        "available": False,
    }
    if favorite.target_type == "lab":
        lab = db.get(Lab, favorite.target_id)
        if lab:
            data.update({"name": lab.name, "status": lab.status, "available": True})
    else:
        equipment = db.get(Equipment, favorite.target_id)
        if equipment:
            data.update({"name": equipment.name, "status": equipment.status, "available": True})
    return data


@router.get("")
def get_favorites(
    target_type: Literal["lab", "equipment"] | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户的收藏列表，可按类型过滤；目标已删除的收藏不返回。"""
    query = db.query(Favorite).filter(Favorite.user_id == current_user.id)
    if target_type:
        query = query.filter(Favorite.target_type == target_type)
    items = query.order_by(Favorite.id.desc()).all()
    rows = [_favorite_to_dict(db, item) for item in items]
    return Response.success(data=[row for row in rows if row["available"]])


@router.post("")
def add_favorite(
    data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """收藏实验室或设备；重复收藏幂等返回已有记录（唯一约束兜底并发）。"""
    if not _target_exists(db, data.target_type, data.target_id):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="收藏目标不存在")
    exists = (
        db.query(Favorite)
        .filter(
            Favorite.user_id == current_user.id,
            Favorite.target_type == data.target_type,
            Favorite.target_id == data.target_id,
        )
        .first()
    )
    if exists:
        return Response.success(message="已收藏", data=_favorite_to_dict(db, exists))
    favorite = Favorite(user_id=current_user.id, target_type=data.target_type, target_id=data.target_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return Response.success(message="收藏成功", data=_favorite_to_dict(db, favorite))


@router.delete("/{favorite_id}")
def delete_favorite(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消收藏：只能删除自己的收藏，别人的收藏按不存在处理。"""
    favorite = db.get(Favorite, favorite_id)
    if not favorite or favorite.user_id != current_user.id:
        raise BusinessException(code=BizCode.NOT_FOUND, message="收藏不存在")
    db.delete(favorite)
    db.commit()
    return Response.success(message="取消收藏成功")
