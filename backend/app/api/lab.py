from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.dependencies.signature import require_signature
from app.models.favorite import Favorite
from app.models.lab import Lab
from app.models.user import User
from app.schemas.lab import LabCreate, LabResponse, LabUpdate

router = APIRouter(prefix="/labs", tags=["实验室管理"])


@router.get("")
def get_lab_list(
    keyword: str = "",
    only_open: bool = False,
    favorite_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询实验室列表；only_open 只展示开放实验室，favorite_only 只看我的收藏。"""
    query = db.query(Lab)
    if keyword.strip():
        query = query.filter(Lab.name.like(f"%{keyword.strip()}%"))
    if only_open:
        query = query.filter(Lab.status == 1)
    if favorite_only:
        # 子查询由数据库完成过滤，避免把所有实验室拉到应用层再筛选。
        query = query.filter(
            Lab.id.in_(
                db.query(Favorite.target_id).filter(
                    Favorite.user_id == current_user.id,
                    Favorite.target_type == "lab",
                )
            )
        )
    labs = query.order_by(Lab.id.desc()).all()
    return Response.success(data=[LabResponse.model_validate(lab) for lab in labs])


@router.post("")
def create_lab(
    data: LabCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if db.query(Lab).filter(Lab.name == data.name.strip()).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室名称已存在")
    lab = Lab(**data.model_dump())
    lab.name = lab.name.strip()
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return Response.success(message="实验室新增成功", data=LabResponse.model_validate(lab))


@router.put("/{lab_id}")
def update_lab(
    lab_id: int,
    data: LabUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lab = db.get(Lab, lab_id)
    if not lab:
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("name"):
        update_data["name"] = update_data["name"].strip()
        exists = db.query(Lab).filter(Lab.name == update_data["name"], Lab.id != lab_id).first()
        if exists:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室名称已存在")
    for field, value in update_data.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return Response.success(message="实验室修改成功", data=LabResponse.model_validate(lab))


@router.delete("/{lab_id}")
def delete_lab(
    lab_id: int,
    _: User = Depends(get_current_admin),
    _sig: User = Depends(require_signature),
    db: Session = Depends(get_db),
):
    lab = db.get(Lab, lab_id)
    if not lab:
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    db.delete(lab)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="实验室已有设备或预约记录，请改为暂停开放",
        )
    return Response.success(message="实验室删除成功")
