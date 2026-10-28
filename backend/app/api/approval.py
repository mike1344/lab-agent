"""审批流管理接口：管理员为实验室配置多级审批节点。"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.permission import get_current_admin
from app.models.approval import ApprovalFlow, ApprovalStep
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.approval import ApprovalFlowUpsert, ApprovalStepInput
from app.services.approval import ROLE_LABELS, step_approver_label, step_label

router = APIRouter(prefix="/approval-flows", tags=["审批流管理"])


def step_to_dict(step: ApprovalStep) -> dict:
    return {
        "id": step.id,
        "step_order": step.step_order,
        "name": step.name,
        "label": step_label(step),
        "approver_type": step.approver_type,
        "approver_role": step.approver_role,
        "approver_role_label": ROLE_LABELS.get(step.approver_role or "", ""),
        "approver_id": step.approver_id,
        "approver_name": step_approver_label(step),
    }


def flow_to_dict(flow: ApprovalFlow, pending_count: int = 0, used_count: int = 0) -> dict:
    return {
        "id": flow.id,
        "lab_id": flow.lab_id,
        "lab_name": flow.lab.name if flow.lab else None,
        "lab_status": flow.lab.status if flow.lab else None,
        "name": flow.name,
        "description": flow.description,
        "enabled": flow.enabled,
        "steps": [step_to_dict(step) for step in flow.steps],
        "pending_count": pending_count,
        "used_count": used_count,
        "create_time": flow.create_time,
        "update_time": flow.update_time,
    }


def _flow_counts(db: Session, flow_id: int) -> tuple[int, int]:
    pending = (
        db.query(func.count(Reservation.id))
        .filter(Reservation.approval_flow_id == flow_id, Reservation.status == "pending")
        .scalar()
        or 0
    )
    used = db.query(func.count(Reservation.id)).filter(Reservation.approval_flow_id == flow_id).scalar() or 0
    return int(pending), int(used)


def _validate_steps(db: Session, steps: list[ApprovalStepInput]) -> list[dict]:
    """校验审批人存在且具备审批资格；按角色审批时要求系统里确实有该角色账号。"""
    normalized = []
    for step in steps:
        if step.approver_type == "user":
            approver = db.get(User, step.approver_id) if step.approver_id else None
            if not approver or not approver.is_active:
                raise BusinessException(code=BizCode.BAD_REQUEST, message="指定的审批人不存在或已被禁用")
            if not approver.is_superuser and not approver.is_teacher:
                raise BusinessException(code=BizCode.BAD_REQUEST, message="指定审批人必须是教师或管理员")
        elif step.approver_role == "teacher":
            available = db.query(User).filter(User.is_active.is_(True), User.is_teacher.is_(True)).count()
            if not available:
                raise BusinessException(code=BizCode.BAD_REQUEST, message="当前没有可用的教师账号，不能按教师角色审批")
        normalized.append(
            {
                "name": step.name,
                "approver_type": step.approver_type,
                "approver_role": step.approver_role,
                "approver_id": step.approver_id,
            }
        )
    return normalized


def _steps_changed(flow: ApprovalFlow, steps: list[dict]) -> bool:
    existing = [
        (step.name, step.approver_type, step.approver_role, step.approver_id)
        for step in sorted(flow.steps, key=lambda item: item.step_order)
    ]
    incoming = [(step["name"], step["approver_type"], step["approver_role"], step["approver_id"]) for step in steps]
    return existing != incoming


def _sync_steps(flow: ApprovalFlow, steps: list[dict]) -> None:
    """按顺序就地更新节点；减少节点时删除尾部多余记录，避免唯一约束冲突。"""
    existing = sorted(flow.steps, key=lambda item: item.step_order)
    for index, payload in enumerate(steps):
        if index < len(existing):
            step = existing[index]
        else:
            step = ApprovalStep(flow=flow, step_order=index + 1)
            flow.steps.append(step)
        step.step_order = index + 1
        step.name = payload["name"]
        step.approver_type = payload["approver_type"]
        step.approver_role = payload["approver_role"]
        step.approver_id = payload["approver_id"]
    for extra in existing[len(steps) :]:
        flow.steps.remove(extra)


@router.get("")
def get_approval_flows(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """审批流列表：管理员查看每个实验室的流程配置与进行中数量。"""
    flows = (
        db.query(ApprovalFlow)
        .options(
            joinedload(ApprovalFlow.lab),
            joinedload(ApprovalFlow.steps).joinedload(ApprovalStep.approver),
        )
        .order_by(ApprovalFlow.id.asc())
        .all()
    )
    if not flows:
        return Response.success(data=[])
    flow_ids = [flow.id for flow in flows]
    pending_rows = dict(
        db.query(Reservation.approval_flow_id, func.count(Reservation.id))
        .filter(Reservation.approval_flow_id.in_(flow_ids), Reservation.status == "pending")
        .group_by(Reservation.approval_flow_id)
        .all()
    )
    used_rows = dict(
        db.query(Reservation.approval_flow_id, func.count(Reservation.id))
        .filter(Reservation.approval_flow_id.in_(flow_ids))
        .group_by(Reservation.approval_flow_id)
        .all()
    )
    data = [flow_to_dict(flow, int(pending_rows.get(flow.id, 0)), int(used_rows.get(flow.id, 0))) for flow in flows]
    return Response.success(data=data)


@router.get("/{lab_id}")
def get_lab_approval_flow(
    lab_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """读取某个实验室的审批流；没有配置时返回 null。"""
    if not db.get(Lab, lab_id):
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    flow = (
        db.query(ApprovalFlow)
        .options(
            joinedload(ApprovalFlow.lab),
            joinedload(ApprovalFlow.steps).joinedload(ApprovalStep.approver),
        )
        .filter(ApprovalFlow.lab_id == lab_id)
        .first()
    )
    if not flow:
        return Response.success(data=None)
    pending, used = _flow_counts(db, flow.id)
    return Response.success(data=flow_to_dict(flow, pending, used))


@router.put("/{lab_id}")
def upsert_lab_approval_flow(
    lab_id: int,
    data: ApprovalFlowUpsert,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """为实验室新建或整体更新审批流；已产生预约的流程不允许再改节点。"""
    lab = db.get(Lab, lab_id)
    if not lab:
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    steps = _validate_steps(db, data.steps)
    flow = (
        db.query(ApprovalFlow)
        .options(joinedload(ApprovalFlow.steps).joinedload(ApprovalStep.approver))
        .filter(ApprovalFlow.lab_id == lab_id)
        .first()
    )
    created = flow is None

    if flow:
        changed = _steps_changed(flow, steps)
        if changed:
            used = db.query(Reservation.id).filter(Reservation.approval_flow_id == flow.id).first()
            if used:
                raise BusinessException(
                    code=BizCode.BAD_REQUEST,
                    message="该审批流已有预约使用，不能再调整审批节点；可修改名称/说明或停用后新建流程",
                )
        flow.name = data.name
        flow.description = data.description
        flow.enabled = data.enabled
        if changed:
            _sync_steps(flow, steps)
    else:
        flow = ApprovalFlow(
            lab_id=lab_id,
            name=data.name,
            description=data.description,
            enabled=data.enabled,
            steps=[
                ApprovalStep(
                    step_order=index + 1,
                    name=step["name"],
                    approver_type=step["approver_type"],
                    approver_role=step["approver_role"],
                    approver_id=step["approver_id"],
                )
                for index, step in enumerate(steps)
            ],
        )
        db.add(flow)

    db.commit()
    db.refresh(flow)
    pending, used = _flow_counts(db, flow.id)
    return Response.success(
        message="审批流已创建" if created else "审批流保存成功",
        data=flow_to_dict(flow, pending, used),
    )


@router.delete("/{flow_id}")
def delete_approval_flow(
    flow_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除未被任何预约使用的审批流；已有预约的流程只能停用，以保留历史。"""
    flow = db.get(ApprovalFlow, flow_id)
    if not flow:
        raise BusinessException(code=BizCode.NOT_FOUND, message="审批流不存在")
    used = db.query(Reservation.id).filter(Reservation.approval_flow_id == flow.id).first()
    if used:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="该审批流已有预约记录，不能删除；如需停止使用请改为停用",
        )
    db.delete(flow)
    db.commit()
    return Response.success(message="审批流已删除")
