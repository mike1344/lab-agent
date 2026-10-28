"""多级审批流的核心逻辑。

设计要点：
1. 预约在创建时快照适用的流程（approval_flow_id）与当前节点，后续流程改名/停用
   不会影响已提交的预约；有预约引用过的流程不允许改节点，保证历史轨迹可解释。
2. 没有配置流程的实验室保持原来的单级审核（任一教师/管理员可直接通过），
   这样存量实验室不需要一次性迁移。
3. 通知与状态推进在业务事务内完成，WebSocket 推送在提交后触发；推送失败不影响
   审批结果，前端轮询/通知列表仍可兜底。
"""

from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode
from app.models.approval import ApprovalFlow, ApprovalStep, ReservationApproval
from app.models.notification import Notification
from app.models.reservation import Reservation
from app.models.user import User
from app.services.ws import push_notification

ROLE_LABELS = {"admin": "管理员", "teacher": "教师"}
ACTION_LABELS = {"approve": "通过", "reject": "拒绝"}


def get_flow_by_lab(db: Session, lab_id: int) -> ApprovalFlow | None:
    """读取实验室的审批流（含节点与指定审批人），供管理与展示复用。"""
    return (
        db.query(ApprovalFlow)
        .options(
            joinedload(ApprovalFlow.lab),
            joinedload(ApprovalFlow.steps).joinedload(ApprovalStep.approver),
        )
        .filter(ApprovalFlow.lab_id == lab_id)
        .first()
    )


def get_active_flow(db: Session, lab_id: int) -> ApprovalFlow | None:
    """只返回启用中的流程；停用的流程不接收新预约。"""
    flow = get_flow_by_lab(db, lab_id)
    if flow and flow.enabled and flow.steps:
        return flow
    return None


def step_label(step: ApprovalStep) -> str:
    """节点显示名：优先使用管理员填写的名称，否则按审批角色生成。"""
    if step.name:
        return step.name
    if step.approver_type == "user" and step.approver:
        return f"{step.approver.full_name or step.approver.username} 审批"
    return f"{ROLE_LABELS.get(step.approver_role or '', '指定人员')}审批"


def step_approver_label(step: ApprovalStep) -> str:
    """审批人描述，写入列表与通知，避免前端再拼装角色文案。"""
    if step.approver_type == "user":
        if step.approver:
            return step.approver.full_name or step.approver.username
        return "已删除用户"
    return ROLE_LABELS.get(step.approver_role or "", "指定人员")


def current_step(reservation: Reservation) -> ApprovalStep | None:
    """预约当前待审批节点；没有流程或节点已不存在时返回 None。"""
    flow = reservation.approval_flow
    if not flow or not reservation.approval_step_order:
        return None
    return next((step for step in flow.steps if step.step_order == reservation.approval_step_order), None)


def approvers_for_step(db: Session, step: ApprovalStep) -> list[User]:
    """节点对应的有效审批人：按角色取全部启用账号，或取指定人员。"""
    if step.approver_type == "user":
        user = db.get(User, step.approver_id) if step.approver_id else None
        return [user] if user and user.is_active else []
    if step.approver_role == "admin":
        return db.query(User).filter(User.is_active.is_(True), User.is_superuser.is_(True)).all()
    if step.approver_role == "teacher":
        return db.query(User).filter(User.is_active.is_(True), User.is_teacher.is_(True)).all()
    return []


def can_user_review(reservation: Reservation, user: User) -> bool:
    """当前用户能否处理这条预约。

    无流程：任一教师/管理员可处理（保持旧行为）；
    有流程：只允许当前节点匹配的审批人。管理员保留兜底能力（避免指定审批人
    离职/停用造成流程永久卡住），但不能审批自己的预约。
    """
    if reservation.status != "pending" or not user.is_active:
        return False
    if not reservation.approval_flow_id:
        return bool(user.is_superuser or user.is_teacher)
    if reservation.user_id == user.id:
        return False
    step = current_step(reservation)
    if step is None:
        return False
    if user.is_superuser:
        return True
    if step.approver_type == "user":
        return step.approver_id == user.id
    if step.approver_role == "admin":
        return user.is_superuser
    return user.is_teacher


def approval_summary(reservation: Reservation, user: User) -> dict | None:
    """预约列表里的轻量审批摘要；没有流程返回 None。"""
    flow = reservation.approval_flow
    if not flow or not reservation.approval_step_order:
        return None
    step = current_step(reservation)
    total = len(flow.steps)
    return {
        "flow_id": flow.id,
        "flow_name": flow.name,
        "current_step": reservation.approval_step_order,
        "total_steps": total,
        "current_step_name": step_label(step) if step else "已完成",
        "current_approver": step_approver_label(step) if step else "",
        "status": "in_progress" if reservation.status == "pending" else reservation.status,
        "can_review": can_user_review(reservation, user),
        "is_requester": reservation.user_id == user.id,
    }


def approval_detail(db: Session, reservation: Reservation, user: User) -> dict:
    """审批进度详情：节点状态、审批轨迹与当前操作权限。"""
    flow = reservation.approval_flow
    if not flow:
        return {
            "flow": None,
            "current_step": None,
            "total_steps": 0,
            "steps": [],
            "decisions": [],
            "can_review": can_user_review(reservation, user),
            "review_mode": "single",
        }

    decisions = {item.step_order: item for item in reservation.approvals}
    steps = []
    current_order = reservation.approval_step_order or 0
    for step in flow.steps:
        decision = decisions.get(step.step_order)
        if decision:
            state = "approved" if decision.action == "approve" else "rejected"
        elif reservation.status == "pending" and step.step_order == current_order:
            state = "pending"
        elif reservation.status == "rejected":
            state = "skipped"
        elif reservation.status == "approved":
            state = "skipped"
        else:
            state = "upcoming"
        steps.append(
            {
                "step_order": step.step_order,
                "name": step_label(step),
                "approver_type": step.approver_type,
                "approver_role": step.approver_role,
                "approver_id": step.approver_id,
                "approver_name": step_approver_label(step),
                "state": state,
                "decision": _decision_to_dict(decision) if decision else None,
            }
        )

    return {
        "flow": {
            "id": flow.id,
            "name": flow.name,
            "description": flow.description,
            "enabled": flow.enabled,
        },
        "current_step": reservation.approval_step_order,
        "total_steps": len(flow.steps),
        "steps": steps,
        "decisions": [_decision_to_dict(item) for item in reservation.approvals],
        "can_review": can_user_review(reservation, user),
        "review_mode": "multi",
    }


def _decision_to_dict(decision: ReservationApproval | None) -> dict | None:
    if decision is None:
        return None
    return {
        "id": decision.id,
        "step_order": decision.step_order,
        "step_name": decision.step_name,
        "approver_id": decision.approver_id,
        "approver_name": (
            (decision.approver.full_name or decision.approver.username) if decision.approver else "未知用户"
        ),
        "action": decision.action,
        "action_label": ACTION_LABELS.get(decision.action, decision.action),
        "comment": decision.comment,
        "create_time": decision.create_time,
    }


def start_approval(reservation: Reservation, flow: ApprovalFlow) -> ApprovalStep | None:
    """创建预约时把流程与首节点写入快照。"""
    reservation.approval_flow_id = flow.id
    reservation.approval_step_order = 1
    return next((step for step in flow.steps if step.step_order == 1), None)


def reset_approval(db: Session, reservation: Reservation) -> ApprovalStep | None:
    """预约内容被修改后清空已完成的审批，从第一节点重新开始。"""
    if not reservation.approval_flow_id:
        return None
    db.query(ReservationApproval).filter(ReservationApproval.reservation_id == reservation.id).delete(
        synchronize_session=False
    )
    reservation.approval_step_order = 1
    reservation.review_comment = None
    db.flush()
    db.refresh(reservation, attribute_names=["approvals"])
    step = current_step(reservation)
    return step


def record_decision(
    db: Session,
    reservation: Reservation,
    step: ApprovalStep,
    approver: User,
    action: str,
    comment: str | None,
) -> None:
    """写入一条不可改写的审批轨迹。"""
    db.add(
        ReservationApproval(
            reservation_id=reservation.id,
            step_order=step.step_order,
            step_name=step_label(step),
            approver_id=approver.id,
            action=action,
            comment=comment,
        )
    )


def create_step_notifications(
    db: Session,
    reservation: Reservation,
    step: ApprovalStep,
) -> list[dict]:
    """给当前节点的审批人落站内通知，返回提交后要推送的 WebSocket 负载。"""
    approvers = [user for user in approvers_for_step(db, step) if user.id != reservation.user_id]
    if not approvers:
        return []

    flow = reservation.approval_flow
    total = len(flow.steps) if flow else 1
    applicant = (
        reservation.user.full_name or reservation.user.username if reservation.user else f"用户{reservation.user_id}"
    )
    span = f"{reservation.reservation_date} {reservation.start_time.strftime('%H:%M')}-{reservation.end_time.strftime('%H:%M')}"
    lab_name = reservation.lab.name if reservation.lab else f"实验室{reservation.lab_id}"
    title = "待审批预约"
    content = (
        f"{applicant} 提交了「{lab_name}」{span} 的预约，"
        f"当前节点：{step_label(step)}（第 {step.step_order}/{total} 步）。请及时处理。"
    )

    payloads = []
    for approver in approvers:
        db.add(
            Notification(
                user_id=approver.id,
                type="approval_pending",
                title=title,
                content=content,
                related_id=reservation.id,
            )
        )
        payloads.append(
            {
                "user_id": approver.id,
                "type": "approval_pending",
                "title": title,
                "content": content,
                "related_id": reservation.id,
            }
        )
    return payloads


def push_pending_notifications(payloads: list[dict]) -> None:
    """在事务提交后统一推送，避免客户端收到尚未落库的消息。"""
    for payload in payloads:
        push_notification(**payload)


def ensure_flow_mutable(db: Session, flow: ApprovalFlow) -> None:
    """有预约引用过流程时禁止改节点，避免历史审批记录与节点对不上。"""
    used = db.query(Reservation.id).filter(Reservation.approval_flow_id == flow.id).first()
    if used:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="该审批流已被预约使用，不能再调整审批节点；可修改名称/说明或停用后新建流程",
        )
