from datetime import date, datetime, time, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode
from app.models.blackout import BlackoutPeriod
from app.models.course import Course
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate
from app.services.approval import (
    create_step_notifications,
    get_active_flow,
    push_pending_notifications,
    start_approval,
)


def check_slot_available(
    db: Session,
    user_id: int,
    lab_id: int,
    current_date: date,
    start_time: time,
    end_time: time,
    exclude_reservation_id: int | None = None,
) -> str | None:
    """校验单个时间段能否预约；返回跳过原因，None 表示可约。

    创建（逐周循环）和修改预约共用这套规则，避免两个入口的校验漂移。
    exclude_reservation_id 供“修改自己的预约”排除自身，避免和旧记录冲突。
    """
    now = datetime.now()
    # 当天开始的预约必须晚于服务器当前时间，避免提交后立刻成为无法履行的记录。
    # 周期预约只有第 0 周可能落在今天，未来周次不受影响。
    if current_date < now.date():
        return str(current_date)
    if current_date == now.date() and start_time <= now.time():
        return f"{current_date}(开始时间已过)"

    # weekly quota check
    iso = current_date.isocalendar()
    week_start = current_date - timedelta(days=iso.weekday - 1)
    week_end = week_start + timedelta(days=6)
    quota_query = db.query(Reservation).filter(
        Reservation.user_id == user_id,
        Reservation.status.in_(["pending", "approved"]),
        Reservation.reservation_date >= week_start,
        Reservation.reservation_date <= week_end,
    )
    if exclude_reservation_id is not None:
        quota_query = quota_query.filter(Reservation.id != exclude_reservation_id)
    if quota_query.count() >= 3:
        return f"{current_date}(本周已达上限)"

    # conflict check
    conflict_query = db.query(Reservation).filter(
        Reservation.lab_id == lab_id,
        Reservation.reservation_date == current_date,
        Reservation.status.in_(["pending", "approved"]),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )
    if exclude_reservation_id is not None:
        conflict_query = conflict_query.filter(Reservation.id != exclude_reservation_id)
    if conflict_query.first():
        return f"{current_date}(时间冲突)"

    # blackout check
    blackout = (
        db.query(BlackoutPeriod)
        .filter(
            BlackoutPeriod.lab_id == lab_id,
            BlackoutPeriod.blackout_date == current_date,
            BlackoutPeriod.start_time < end_time,
            BlackoutPeriod.end_time > start_time,
        )
        .first()
    )
    if blackout:
        return f"{current_date}({blackout.reason})"

    # course check：课表按周重复占用实验室，与自由预约共用同一套重叠判定
    course = (
        db.query(Course)
        .filter(
            Course.lab_id == lab_id,
            Course.weekday == current_date.isoweekday(),
            Course.start_date <= current_date,
            Course.end_date >= current_date,
            Course.start_time < end_time,
            Course.end_time > start_time,
        )
        .first()
    )
    if course:
        return f"{current_date}(课程《{course.name}》占用)"
    return None


def create_reservation_record(
    db: Session,
    user_id: int,
    data: ReservationCreate,
):
    """Create reservation (supports weekly repeat). Returns (created_list, skipped_list)."""
    lab = db.query(Lab).filter(Lab.id == data.lab_id).with_for_update().first()
    if not lab or lab.status != 1:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="实验室不存在或未开放",
        )

    # single session duration limit
    duration = datetime.combine(data.reservation_date, data.end_time) - datetime.combine(
        data.reservation_date, data.start_time
    )
    if duration.total_seconds() > 4 * 3600:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="单次预约不能超过 4 小时",
        )

    # 流程只在提交时取一次：同一次周期预约的每一周都进入同一条流程的首节点。
    flow = get_active_flow(db, data.lab_id)
    created = []
    skipped = []
    approval_payloads = []

    for week_offset in range(data.repeat_weeks):
        current_date = data.reservation_date + timedelta(weeks=week_offset)
        reason = check_slot_available(
            db,
            user_id,
            data.lab_id,
            current_date,
            data.start_time,
            data.end_time,
        )
        if reason:
            skipped.append(reason)
            continue

        reservation = Reservation(
            user_id=user_id,
            status="pending",
            lab_id=data.lab_id,
            reservation_date=current_date,
            start_time=data.start_time,
            end_time=data.end_time,
            purpose=data.purpose,
        )
        db.add(reservation)
        db.flush()
        if flow:
            step = start_approval(reservation, flow)
            if step:
                db.flush()
                approval_payloads.extend(create_step_notifications(db, reservation, step))
        created.append(reservation)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="预约创建失败",
        ) from exc

    for r in created:
        db.refresh(r)
    # 通知已随预约一起提交；WebSocket 推送放在提交之后，避免推送到尚未落库的数据。
    push_pending_notifications(approval_payloads)
    return created, skipped
