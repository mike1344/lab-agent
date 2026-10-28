from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.dependencies.signature import require_signature
from app.models.equipment import Equipment
from app.models.favorite import Favorite
from app.models.lab import Lab
from app.models.user import User
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate
from app.services.export import build_excel_response

router = APIRouter(prefix="/equipment", tags=["设备管理"])


def equipment_to_dict(equipment: Equipment) -> dict:
    """把关联的实验室名称一起整理给前端，避免前端再次请求。"""
    return {
        "id": equipment.id,
        "lab_id": equipment.lab_id,
        "lab_name": equipment.lab.name if equipment.lab else None,
        "name": equipment.name,
        "code": equipment.code,
        "quantity": equipment.quantity,
        "description": equipment.description,
        "usage_doc_url": equipment.usage_doc_url,
        "status": equipment.status,
        "create_time": equipment.create_time,
        "update_time": equipment.update_time,
    }


@router.get("")
def get_equipment_list(
    lab_id: int | None = None,
    keyword: str = "",
    only_available: bool = False,
    favorite_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """设备列表；only_available 只看可用设备，favorite_only 只看我的收藏。"""
    query = db.query(Equipment).options(joinedload(Equipment.lab))
    if lab_id:
        query = query.filter(Equipment.lab_id == lab_id)
    if keyword.strip():
        query = query.filter(Equipment.name.like(f"%{keyword.strip()}%"))
    if only_available:
        query = query.filter(Equipment.status == 1, Equipment.quantity > 0)
    if favorite_only:
        query = query.filter(
            Equipment.id.in_(
                db.query(Favorite.target_id).filter(
                    Favorite.user_id == current_user.id,
                    Favorite.target_type == "equipment",
                )
            )
        )
    equipment_list = query.order_by(Equipment.id.desc()).all()
    return Response.success(data=[equipment_to_dict(item) for item in equipment_list])


@router.post("")
def create_equipment(
    data: EquipmentCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Lab, data.lab_id):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="所属实验室不存在")
    if db.query(Equipment).filter(Equipment.code == data.code.strip()).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="设备编号已存在")
    equipment = Equipment(**data.model_dump())
    equipment.name = equipment.name.strip()
    equipment.code = equipment.code.strip()
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return Response.success(message="设备新增成功", data=equipment_to_dict(equipment))


@router.put("/{equipment_id}")
def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise BusinessException(code=BizCode.NOT_FOUND, message="设备不存在")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("lab_id") and not db.get(Lab, update_data["lab_id"]):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="所属实验室不存在")
    if update_data.get("code"):
        update_data["code"] = update_data["code"].strip()
        exists = db.query(Equipment).filter(Equipment.code == update_data["code"], Equipment.id != equipment_id).first()
        if exists:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="设备编号已存在")
    for field, value in update_data.items():
        setattr(equipment, field, value)
    db.commit()
    db.refresh(equipment)
    return Response.success(message="设备修改成功", data=equipment_to_dict(equipment))


@router.get("/export")
def export_equipment(
    lab_id: int | None = None,
    keyword: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员导出设备台账（与列表筛选一致）。"""
    query = db.query(Equipment).options(joinedload(Equipment.lab))
    if lab_id:
        query = query.filter(Equipment.lab_id == lab_id)
    if keyword.strip():
        query = query.filter(Equipment.name.like(f"%{keyword.strip()}%"))
    items = query.order_by(Equipment.id.desc()).all()
    rows = [
        [
            item.code,
            item.name,
            item.lab.name if item.lab else "",
            item.quantity,
            "正常" if item.status == 1 else "维护中",
            item.description or "",
            item.usage_doc_url or "",
            str(item.create_time),
        ]
        for item in items
    ]
    return build_excel_response(
        sheet_title="设备台账",
        headers=["设备编号", "设备名称", "所属实验室", "数量", "状态", "设备说明", "操作说明链接", "创建时间"],
        rows=rows,
        filename_prefix="设备台账",
    )


@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    _: User = Depends(get_current_admin),
    _sig: User = Depends(require_signature),
    db: Session = Depends(get_db),
):
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise BusinessException(code=BizCode.NOT_FOUND, message="设备不存在")
    db.delete(equipment)
    db.commit()
    return Response.success(message="设备删除成功")
