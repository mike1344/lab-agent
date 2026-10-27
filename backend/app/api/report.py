"""报表中心：按时间范围统计机时与预估费用，按实验室/用户两个维度汇总。

口径约定：
- 「预约次数」统计区间内全部状态的预约；
- 「机时」只统计状态为 approved 的预约（pending/rejected/expired 不计费）；
- 课程机时按课表在区间内的实际occurrence 次数折算；
- 费用 = 机时 × `LAB_HOUR_RATE`（.env 配置，0 表示不计算费用）。
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.config import settings
from app.database import get_db
from app.dependencies.permission import get_current_staff
from app.models.course import Course
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.services.export import build_excel_response

router = APIRouter(prefix="/reports", tags=["报表中心"])


def _duration_hours(start, end) -> float:
    """单个预约的时长（小时）。"""
    delta = datetime.combine(date.min, end) - datetime.combine(date.min, start)
    return max(0.0, delta.total_seconds() / 3600)


def _occurrences(start: date, end: date, weekday: int) -> int:
    """统计 [start, end] 区间内某个星期几（1-7）出现的次数。"""
    if end < start:
        return 0
    total_days = (end - start).days + 1
    count = total_days // 7
    remainder = total_days % 7
    first_weekday = start.isoweekday()
    extra = any(((first_weekday + offset - 1) % 7) + 1 == weekday for offset in range(remainder))
    return count + (1 if extra else 0)


def _build_report(db: Session, start: date, end: date, lab_id: int | None) -> dict:
    """核心计算：返回 totals / by_lab / by_user 三段结果。"""
    lab_query = db.query(Lab)
    if lab_id:
        lab_query = lab_query.filter(Lab.id == lab_id)
    labs = lab_query.all()

    reservations = (
        db.query(Reservation)
        .options(joinedload(Reservation.user))
        .filter(
            Reservation.reservation_date >= start,
            Reservation.reservation_date <= end,
        )
        .all()
    )
    if lab_id:
        reservations = [item for item in reservations if item.lab_id == lab_id]

    by_lab: dict[int, dict] = {
        lab.id: {
            "lab_id": lab.id,
            "lab_name": lab.name,
            "reservations": 0,
            "approved": 0,
            "hours": 0.0,
            "users": set(),
            "course_hours": 0.0,
        }
        for lab in labs
    }
    by_user: dict[int, dict] = {}
    approved_hours = 0.0

    for reservation in reservations:
        lab_entry = by_lab.get(reservation.lab_id)
        user_id = reservation.user_id
        user_entry = by_user.setdefault(
            user_id,
            {
                "user_id": user_id,
                "username": reservation.user.full_name or reservation.user.username,
                "reservations": 0,
                "approved": 0,
                "hours": 0.0,
            },
        )
        if lab_entry:
            lab_entry["reservations"] += 1
            lab_entry["users"].add(user_id)
        user_entry["reservations"] += 1
        if reservation.status != "approved":
            continue

        hours = _duration_hours(reservation.start_time, reservation.end_time)
        approved_hours += hours
        if lab_entry:
            lab_entry["approved"] += 1
            lab_entry["hours"] += hours
        user_entry["approved"] += 1
        user_entry["hours"] += hours

    # 课程机时：课表按周重复，按区间内实际发生次数折算
    course_query = db.query(Course)
    if lab_id:
        course_query = course_query.filter(Course.lab_id == lab_id)
    for course in course_query.all():
        window_start = max(start, course.start_date)
        window_end = min(end, course.end_date)
        occurrences = _occurrences(window_start, window_end, course.weekday)
        if not occurrences:
            continue
        lab_entry = by_lab.get(course.lab_id)
        if lab_entry:
            lab_entry["course_hours"] += occurrences * _duration_hours(course.start_time, course.end_time)

    rate = settings.LAB_HOUR_RATE
    lab_rows = []
    for entry in by_lab.values():
        entry["users"] = len(entry["users"])
        entry["hours"] = round(entry["hours"], 2)
        entry["course_hours"] = round(entry["course_hours"], 2)
        entry["estimated_cost"] = round(entry["hours"] * rate, 2)
        lab_rows.append(entry)
    lab_rows.sort(key=lambda item: item["hours"], reverse=True)

    user_rows = []
    for entry in by_user.values():
        entry["hours"] = round(entry["hours"], 2)
        entry["estimated_cost"] = round(entry["hours"] * rate, 2)
        user_rows.append(entry)
    user_rows.sort(key=lambda item: item["hours"], reverse=True)

    total_users = len({item["user_id"] for item in by_user.values()})
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hour_rate": rate,
        "totals": {
            "reservations": len(reservations),
            "approved": sum(1 for item in reservations if item.status == "approved"),
            "hours": round(approved_hours, 2),
            "users": total_users,
            "course_hours": round(sum(row["course_hours"] for row in lab_rows), 2),
            "estimated_cost": round(approved_hours * rate, 2),
        },
        "by_lab": lab_rows,
        "by_user": user_rows,
    }


def _parse_range(start_date: str, end_date: str) -> tuple[date, date]:
    default_end = date.today()
    default_start = default_end - timedelta(days=29)
    start = date.fromisoformat(start_date) if start_date else default_start
    end = date.fromisoformat(end_date) if end_date else default_end
    if end < start:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="结束日期不能早于开始日期")
    return start, end


@router.get("/usage")
def get_usage_report(
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    lab_id: int | None = None,
    _: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """机时报表：默认最近 30 天，返回汇总、按实验室、按用户三段数据。"""
    try:
        start, end = _parse_range(start_date, end_date)
    except ValueError:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="日期格式应为 YYYY-MM-DD")
    return Response.success(data=_build_report(db, start, end, lab_id))


@router.get("/usage/export")
def export_usage_report(
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    lab_id: int | None = None,
    _: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """导出机时报表：按实验室、按用户两个工作表。"""
    try:
        start, end = _parse_range(start_date, end_date)
    except ValueError:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="日期格式应为 YYYY-MM-DD")
    report = _build_report(db, start, end, lab_id)
    lab_rows = [
        [
            row["lab_name"],
            row["reservations"],
            row["approved"],
            row["hours"],
            row["course_hours"],
            row["users"],
            row["estimated_cost"],
        ]
        for row in report["by_lab"]
    ]
    user_rows = [
        [
            row["username"],
            row["reservations"],
            row["approved"],
            row["hours"],
            row["estimated_cost"],
        ]
        for row in report["by_user"]
    ]
    return build_excel_response(
        sheet_title="按实验室",
        headers=["实验室", "预约次数", "已通过", "机时(小时)", "课程机时(小时)", "使用人数", "预估费用(元)"],
        rows=lab_rows,
        filename_prefix="机时报表",
        extra_sheets=[
            (
                "按用户",
                ["用户", "预约次数", "已通过", "机时(小时)", "预估费用(元)"],
                user_rows,
            )
        ],
    )
