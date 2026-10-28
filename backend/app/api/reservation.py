from datetime import date, datetime, timedelta
from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import Response as FastAPIResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin, get_current_staff
from app.dependencies.signature import verify_signature
from app.models.blackout import BlackoutPeriod
from app.models.lab import Lab
from app.models.notification import Notification
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationReview, ReservationUpdate
from app.services import email as email_service
from app.services.reservation import check_slot_available, create_reservation_record
from app.services.ws import push_notification

router = APIRouter(prefix="/reservations", tags=["实验室预约"])


def reservation_to_dict(reservation: Reservation) -> dict:
    """将预约及其关联对象转换成前端直接可展示的数据。"""
    return {
        "id": reservation.id,
        "user_id": reservation.user_id,
        "user_name": reservation.user.full_name or reservation.user.username,
        "lab_id": reservation.lab_id,
        "lab_name": reservation.lab.name,
        "reservation_date": reservation.reservation_date,
        "start_time": reservation.start_time,
        "end_time": reservation.end_time,
        "purpose": reservation.purpose,
        "status": reservation.status,
        "review_comment": reservation.review_comment,
        "create_time": reservation.create_time,
    }


def reservation_query(db: Session):
    """所有预约查询统一预加载用户与实验室，防止列表出现 N+1 查询。"""
    return db.query(Reservation).options(joinedload(Reservation.user), joinedload(Reservation.lab))


@router.post("")
def create_reservation(
    data: ReservationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生提交预约，初始状态为待审核。支持每周重复。"""
    created, skipped = create_reservation_record(db, current_user.id, data)
    if not created:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message=f"预约失败：{'；'.join(skipped)}",
        )
    # 重新读取以加载关联信息
    ids = [r.id for r in created]
    reservations = reservation_query(db).filter(Reservation.id.in_(ids)).all()
    msg = f"成功创建 {len(created)} 条预约"
    if skipped:
        msg += f"，跳过 {len(skipped)} 周（{'；'.join(skipped)}）"
    return Response.success(message=msg, data=[reservation_to_dict(r) for r in reservations])


@router.get("/mine")
def get_my_reservations(
    status: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = reservation_query(db).filter(Reservation.user_id == current_user.id)
    if status:
        query = query.filter(Reservation.status == status)
    items = query.order_by(Reservation.id.desc()).all()
    return Response.success(data=[reservation_to_dict(item) for item in items])


@router.get("/slots")
def get_occupied_slots(
    lab_id: int,
    reservation_date: date,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询某实验室某天已被占用的时段（待审核 + 已通过）。

    供前端在预约前做可视化展示：学生选定实验室和日期后，先拿到已有的
    占用时段，把冲突时间段标出来，避免提交后才被告知无法预约。
    """
    if not db.query(Lab).filter(Lab.id == lab_id).first():
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    slots = (
        reservation_query(db)
        .filter(
            Reservation.lab_id == lab_id,
            Reservation.reservation_date == reservation_date,
            Reservation.status.in_(["pending", "approved"]),
        )
        .order_by(Reservation.start_time, Reservation.end_time)
        .all()
    )
    return Response.success(
        data={
            "occupied": [
                {
                    "id": item.id,
                    "user_name": item.user.full_name or item.user.username,
                    "start_time": item.start_time,
                    "end_time": item.end_time,
                    "status": item.status,
                    "purpose": item.purpose,
                }
                for item in slots
            ],
            "blackouts": [
                {
                    "start_time": str(b.start_time),
                    "end_time": str(b.end_time),
                    "reason": b.reason,
                }
                for b in db.query(BlackoutPeriod)
                .filter(
                    BlackoutPeriod.lab_id == lab_id,
                    BlackoutPeriod.blackout_date == reservation_date,
                )
                .all()
            ],
        }
    )


@router.get("/calendar")
def get_reservation_calendar(
    lab_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """周/日视图数据源：返回一段日期内某实验室的预约占用与不可约时段。

    与 /slots 的区别：/slots 只看一天，本接口一次返回整段日期范围，
    供前端把同一实验室的多天占用渲染成周历（周一到周日）或单日详细视图。
    """
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")

    # 日期范围规则：两端都缺省时取当前周（周一为一周起点）；
    # 只给一端时按 7 天补齐；单次查询最多 31 天，防止无限制拉取。
    today = date.today()
    if start_date is None and end_date is None:
        start_date = today - timedelta(days=today.weekday())
    elif start_date is None:
        start_date = end_date - timedelta(days=6)
    if end_date is None:
        end_date = start_date + timedelta(days=6)
    if end_date < start_date:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="结束日期不能早于开始日期")
    if (end_date - start_date).days + 1 > 31:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="单次查询不能超过 31 天")

    # 只查 pending/approved：日历展示的是“占用”，被拒和已取消不占时间线，
    # 与创建预约时的冲突校验口径保持一致。
    reservations = (
        reservation_query(db)
        .filter(
            Reservation.lab_id == lab_id,
            Reservation.reservation_date >= start_date,
            Reservation.reservation_date <= end_date,
            Reservation.status.in_(["pending", "approved"]),
        )
        .order_by(Reservation.reservation_date, Reservation.start_time)
        .all()
    )
    blackouts = (
        db.query(BlackoutPeriod)
        .filter(
            BlackoutPeriod.lab_id == lab_id,
            BlackoutPeriod.blackout_date >= start_date,
            BlackoutPeriod.blackout_date <= end_date,
        )
        .order_by(BlackoutPeriod.blackout_date, BlackoutPeriod.start_time)
        .all()
    )
    return Response.success(
        data={
            "range": {"start_date": str(start_date), "end_date": str(end_date)},
            "lab": {"id": lab.id, "name": lab.name, "status": lab.status},
            "reservations": [
                {
                    "id": item.id,
                    "reservation_date": str(item.reservation_date),
                    "start_time": str(item.start_time),
                    "end_time": str(item.end_time),
                    "user_name": item.user.full_name or item.user.username,
                    "purpose": item.purpose,
                    "status": item.status,
                }
                for item in reservations
            ],
            "blackouts": [
                {
                    "blackout_date": str(item.blackout_date),
                    "start_time": str(item.start_time),
                    "end_time": str(item.end_time),
                    "reason": item.reason,
                }
                for item in blackouts
            ],
        }
    )


@router.put("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 与管理员审核锁定同一条预约行，避免双方同时读取 pending 后互相覆盖结果。
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if not reservation or reservation.user_id != current_user.id:
        raise BusinessException(code=BizCode.NOT_FOUND, message="预约记录不存在")
    if reservation.status not in ("pending", "approved"):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="当前状态不能取消")
    reservation.status = "cancelled"
    db.commit()
    return Response.success(message="预约已取消")


@router.put("/{reservation_id}")
def update_reservation(
    reservation_id: int,
    data: ReservationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生修改自己待审核的预约；修改后的时间段同样要满足预约规则。"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if not reservation or reservation.user_id != current_user.id:
        raise BusinessException(code=BizCode.NOT_FOUND, message="预约记录不存在")
    if reservation.status != "pending":
        raise BusinessException(code=BizCode.BAD_REQUEST, message="只有待审核的预约才能修改")

    update_data = data.model_dump(exclude_unset=True)
    effective_date = update_data.get("reservation_date", reservation.reservation_date)
    effective_start = update_data.get("start_time", reservation.start_time)
    effective_end = update_data.get("end_time", reservation.end_time)
    if effective_start >= effective_end:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="结束时间必须晚于开始时间")
    duration = datetime.combine(effective_date, effective_end) - datetime.combine(effective_date, effective_start)
    if duration.total_seconds() > 4 * 3600:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="单次预约不能超过 4 小时")

    # 创建时的冲突、黑名单、周配额和当天时间规则，修改时同样不能绕过。
    reason = check_slot_available(
        db,
        current_user.id,
        reservation.lab_id,
        effective_date,
        effective_start,
        effective_end,
        exclude_reservation_id=reservation.id,
    )
    if reason:
        raise BusinessException(code=BizCode.BAD_REQUEST, message=f"修改失败：{reason}")

    for field, value in update_data.items():
        setattr(reservation, field, value)
    db.commit()
    reservation = reservation_query(db).filter(Reservation.id == reservation.id).first()
    return Response.success(message="预约已修改", data=reservation_to_dict(reservation))


@router.get("")
def get_reservation_list(
    status: str = "",
    lab_id: int | None = None,
    _: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """管理员/教师查看全部预约，并可按状态和实验室筛选。"""
    query = reservation_query(db)
    if status:
        query = query.filter(Reservation.status == status)
    if lab_id:
        query = query.filter(Reservation.lab_id == lab_id)
    items = query.order_by(Reservation.id.desc()).all()
    return Response.success(data=[reservation_to_dict(item) for item in items])


@router.put("/{reservation_id}/review")
def review_reservation(
    reservation_id: int,
    data: ReservationReview,
    background: BackgroundTasks,
    signature_password: str = Query(default=""),
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """管理员审核预约，只允许通过或拒绝。"""
    if data.status not in ("approved", "rejected"):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="审核状态不正确")
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if not reservation:
        raise BusinessException(code=BizCode.NOT_FOUND, message="预约记录不存在")
    if reservation.status != "pending":
        raise BusinessException(code=BizCode.BAD_REQUEST, message="该预约已经处理")

    # 驳回属于危险操作：要求二次输入密码（电子签名），与操作日志共同留痕
    if data.status == "rejected":
        verify_signature(signature_password, current_user)

    # 邮件在提交后由 BackgroundTasks 异步发送，先取好收件人避免会话关闭后懒加载
    recipient_email = reservation.user.email if reservation.user else ""

    if data.status == "approved":
        # 从提交到审核期间，日期可能已经过去，实验室也可能被管理员暂停开放。
        # 审核前复核一次，避免批准已经无法履行的预约。
        now = datetime.now()
        if reservation.reservation_date < now.date() or (
            reservation.reservation_date == now.date() and reservation.start_time <= now.time()
        ):
            raise BusinessException(code=BizCode.BAD_REQUEST, message="预约时间已经过去，不能通过审核")
        lab = db.query(Lab).filter(Lab.id == reservation.lab_id).with_for_update().first()
        if not lab or lab.status != 1:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室当前未开放，不能通过审核")

    reservation.status = data.status
    reservation.review_comment = data.review_comment

    # 审核结果自动生成站内通知，并尝试 WebSocket 实时推送（用户不在线时靠轮询兜底）
    lab_name = reservation.lab.name if reservation.lab else "未知实验室"
    time_text = f"{reservation.reservation_date} {reservation.start_time}-{reservation.end_time}"
    if data.status == "approved":
        notif_title = "预约审核已通过"
        notif_content = f"你预约的「{lab_name}」{time_text} 已审核通过，请按时到场。"
    else:
        notif_title = "预约未通过"
        notif_content = f"你预约的「{lab_name}」{time_text} 未通过审核。原因：{data.review_comment or '无'}"
    db.add(
        Notification(
            user_id=reservation.user_id,
            type="reservation_result",
            title=notif_title,
            content=notif_content,
            related_id=reservation.id,
        )
    )

    db.commit()
    push_notification(
        user_id=reservation.user_id,
        type="reservation_result",
        title=notif_title,
        content=notif_content,
        related_id=reservation.id,
    )
    background.add_task(email_service.send_notification_email, recipient_email, notif_title, notif_content)
    return Response.success(message="预约审核完成")


@router.get("/export")
def export_reservations(
    status: str = "",
    lab_id: int | None = None,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员导出预约记录为 Excel。"""
    query = reservation_query(db)
    if status:
        query = query.filter(Reservation.status == status)
    if lab_id:
        query = query.filter(Reservation.lab_id == lab_id)
    items = query.order_by(Reservation.id.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "预约记录"
    headers = ["ID", "预约人", "实验室", "日期", "开始时间", "结束时间", "用途", "状态", "审核意见", "创建时间"]
    ws.append(headers)
    status_map = {"pending": "待审核", "approved": "已通过", "rejected": "已拒绝", "cancelled": "已取消"}
    for item in items:
        ws.append(
            [
                item.id,
                item.user.full_name or item.user.username,
                item.lab.name,
                str(item.reservation_date),
                str(item.start_time),
                str(item.end_time),
                item.purpose,
                status_map.get(item.status, item.status),
                item.review_comment or "",
                str(item.create_time),
            ]
        )

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"预约记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return FastAPIResponse(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
