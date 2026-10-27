from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.permission import get_current_admin
from app.models.equipment import Equipment
from app.models.procurement import Procurement
from app.models.user import User
from app.schemas.procurement import ProcurementCreate, ProcurementUpdate

router = APIRouter(prefix="/procurements", tags=["设备采购"])

STATUS_LABELS = {"pending": "申请中", "arrived": "已到货", "accepted": "已验收"}


def procurement_to_dict(item: Procurement) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "quantity": item.quantity,
        "equipment_id": item.equipment_id,
        "equipment_name": item.equipment.name if item.equipment else None,
        "applicant_id": item.applicant_id,
        "applicant_name": item.applicant.full_name or item.applicant.username if item.applicant else None,
        "status": item.status,
        "status_label": STATUS_LABELS.get(item.status, item.status),
        "remark": item.remark,
        "create_time": item.create_time,
        "update_time": item.update_time,
    }


def _query(db: Session):
    return db.query(Procurement).options(joinedload(Procurement.equipment), joinedload(Procurement.applicant))


@router.get("")
def get_procurement_list(
    status: str = "",
    keyword: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员查看采购记录，可按状态与物品名称过滤。"""
    query = _query(db)
    if status.strip():
        query = query.filter(Procurement.status == status.strip())
    if keyword.strip():
        query = query.filter(Procurement.name.like(f"%{keyword.strip()}%"))
    items = query.order_by(Procurement.id.desc()).all()
    return Response.success(data=[procurement_to_dict(item) for item in items])


@router.post("")
def create_procurement(
    data: ProcurementCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """录入采购申请（默认 pending）。"""
    name = data.name.strip()
    if len(name) < 2:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="采购物品名称至少需要 2 个字符")
    if data.equipment_id is not None and not db.get(Equipment, data.equipment_id):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="关联设备不存在")
    item = Procurement(
        equipment_id=data.equipment_id,
        name=name,
        quantity=data.quantity,
        applicant_id=current_user.id,
        status="pending",
        remark=data.remark.strip() if data.remark else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    item = _query(db).filter(Procurement.id == item.id).first()
    return Response.success(message="采购申请已录入", data=procurement_to_dict(item))


@router.put("/{procurement_id}")
def update_procurement_status(
    procurement_id: int,
    data: ProcurementUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """推进采购状态：pending→arrived→accepted；验收时把数量计入设备库存。"""
    item = db.get(Procurement, procurement_id)
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="采购记录不存在")

    # 状态机：只允许前进一步，禁止回退或跳级，防止重复入库
    allowed_from = {"arrived": "pending", "accepted": "arrived"}
    if item.status != allowed_from[data.status]:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message=f"当前状态为「{STATUS_LABELS.get(item.status, item.status)}」，"
            f"不能直接变更为「{STATUS_LABELS[data.status]}」",
        )

    if data.equipment_id is not None:
        if not db.get(Equipment, data.equipment_id):
            raise BusinessException(code=BizCode.BAD_REQUEST, message="关联设备不存在")
        item.equipment_id = data.equipment_id
    if data.remark is not None:
        item.remark = data.remark.strip() or None

    if data.status == "accepted":
        if not item.equipment_id:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="验收前请先关联设备")
        equipment = db.get(Equipment, item.equipment_id)
        # 入库：采购数量计入设备库存
        equipment.quantity += item.quantity

    item.status = data.status
    db.commit()
    db.refresh(item)
    item = _query(db).filter(Procurement.id == item.id).first()
    return Response.success(message=f"状态已更新为「{STATUS_LABELS[data.status]}」", data=procurement_to_dict(item))


@router.delete("/{procurement_id}")
def delete_procurement(
    procurement_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除采购记录：已验收的记录保留审计轨迹，不允许删除。"""
    item = db.get(Procurement, procurement_id)
    if not item:
        raise BusinessException(code=BizCode.NOT_FOUND, message="采购记录不存在")
    if item.status == "accepted":
        raise BusinessException(code=BizCode.BAD_REQUEST, message="已验收的记录不允许删除")
    db.delete(item)
    db.commit()
    return Response.success(message="采购记录删除成功")
