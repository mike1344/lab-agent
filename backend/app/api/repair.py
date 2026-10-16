from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.models.notification import Notification
from app.models.repair import Repair
from app.models.user import User
from app.schemas.repair import RepairCreate, RepairHandle

router = APIRouter(prefix="/repairs", tags=["实验室报修"])


def repair_to_dict(item: Repair) -> dict:
    return {
        "id": item.id,
        "reporter_id": item.reporter_id,
        "reporter_name": item.reporter.full_name or item.reporter.username,
        "lab_id": item.lab_id,
        "lab_name": item.lab.name if item.lab else None,
        "equipment_id": item.equipment_id,
        "equipment_name": item.equipment.name if item.equipment else None,
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "handle_comment": item.handle_comment,
        "handler_id": item.handler_id,
        "handler_name": (item.handler.full_name or item.handler.username) if item.handler else None,
        "create_time": item.create_time,
        "update_time": item.update_time,
    }


def repair_query(db: Session):
    return db.query(Repair).options(
        joinedload(Repair.reporter),
        joinedload(Repair.handler),
        joinedload(Repair.lab),
        joinedload(Repair.equipment),
    )


@router.post("")
def create_repair(
    data: RepairCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生提交报修申请。"""
    if data.lab_id and not db.query(Lab).filter(Lab.id == data.lab_id).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="关联实验室不存在")
    if data.equipment_id and not db.query(Equipment).filter(Equipment.id == data.equipment_id).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="关联设备不存在")
    item = Repair(reporter_id=current_user.id, status="pending", **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    item = repair_query(db).filter(Repair.id == item.id).first()
    return Response.success(message="报修提交成功", data=repair_to_dict(item))


@router.get("/mine")
def get_my_repairs(
    status: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生查看自己提交的报修记录。"""
    query = repair_query(db).filter(Repair.reporter_id == current_user.id)
    if status:
        query = query.filter(Repair.status == status)
    items = query.order_by(Repair.id.desc()).all()
    return Response.success(data=[repair_to_dict(item) for item in items])


@router.get("")
def get_repair_list(
    status: str = "",
    lab_id: int | None = None,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员查看全部报修记录，可按状态和实验室筛选。"""
    query = repair_query(db)
    if status:
        query = query.filter(Repair.status == status)
    if lab_id:
        query = query.filter(Repair.lab_id == lab_id)
    items = query.order_by(Repair.id.desc()).all()
    return Response.success(data=[repair_to_dict(item) for item in items])


@router.get("/{repair_id}")
def get_repair_detail(
    repair_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看报修详情；学生只能看自己的，管理员可看全部。"""
    item = repair_query(db).filter(Repair.id == repair_id).first()
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="报修记录不存在")
    if not current_user.is_superuser and item.reporter_id != current_user.id:
        raise BusinessException(code=BizCode.FORBIDDEN, message="无权查看该报修记录")
    return Response.success(data=repair_to_dict(item))


@router.put("/{repair_id}/handle")
def handle_repair(
    repair_id: int,
    data: RepairHandle,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员处理报修：更新状态（处理中/已解决）并填写处理备注。"""
    if data.status not in ("processing", "resolved"):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="处理状态不正确")
    item = (
        db.query(Repair)
        .filter(Repair.id == repair_id)
        .with_for_update()
        .first()
    )
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="报修记录不存在")
    item.status = data.status
    item.handle_comment = data.handle_comment
    item.handler_id = current_user.id

    # 处理结果生成站内通知，学生不需要反复回来看进度。
    status_text = "处理中" if data.status == "processing" else "已解决"
    db.add(
        Notification(
            user_id=item.reporter_id,
            type="repair_result",
            title=f"报修进度更新：{status_text}",
            content=f"你提交的报修「{item.title}」状态已更新为{status_text}。处理备注：{data.handle_comment or '无'}",
            related_id=item.id,
        )
    )
    db.commit()
    item = repair_query(db).filter(Repair.id == item.id).first()
    return Response.success(message="报修处理完成", data=repair_to_dict(item))
