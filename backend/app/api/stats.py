from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.repair import Repair
from app.models.reservation import Reservation
from app.models.user import User

router = APIRouter(prefix="/stats", tags=["首页统计"])


@router.get("/summary")
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """首页统计：管理员看全局，学生只看自己的预约。"""
    reservation_query = db.query(func.count(Reservation.id))
    pending_query = reservation_query.filter(Reservation.status == "pending")
    if not current_user.is_superuser:
        reservation_query = reservation_query.filter(Reservation.user_id == current_user.id)
        pending_query = pending_query.filter(Reservation.user_id == current_user.id)

    data = {
        "lab_count": db.query(func.count(Lab.id)).filter(Lab.status == 1).scalar() or 0,
        "equipment_count": db.query(func.coalesce(func.sum(Equipment.quantity), 0))
        .filter(Equipment.status == 1)
        .scalar()
        or 0,
        "reservation_count": reservation_query.scalar() or 0,
        "pending_count": pending_query.scalar() or 0,
    }
    if current_user.is_superuser:
        data["user_count"] = db.query(func.count(User.id)).scalar() or 0
    return Response.success(data=data)


@router.get("/dashboard")
def get_dashboard(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """首页图表数据：预约趋势、实验室使用排行、报修状态分布。

    口径与 /summary 一致：教师/管理员看全局，学生只看自己的数据。
    """
    # 1) 参数收敛：允许 1~90 天，默认 7 天，防止异常参数拖垮聚合查询。
    days = min(max(days, 1), 90)
    is_staff = current_user.is_superuser or current_user.is_teacher

    today = date.today()
    start_date = today - timedelta(days=days - 1)

    # 2) 预约趋势：按“创建日期 + 状态”分组聚合，Python 侧补零并透视。
    #    用 create_time 而不是 reservation_date——趋势反映“每天新增了多少预约”，
    #    预约日期本身可以是未来任意一天。
    trend_query = db.query(
        func.date(Reservation.create_time).label("day"),
        Reservation.status,
        func.count(Reservation.id),
    ).filter(func.date(Reservation.create_time) >= start_date)
    if not is_staff:
        trend_query = trend_query.filter(Reservation.user_id == current_user.id)
    counters: dict[str, dict[str, int]] = {}
    for day, status, count in trend_query.group_by("day", Reservation.status).all():
        counters.setdefault(str(day), {})[status] = int(count)

    reservation_trend = []
    for offset in range(days):
        d = str(start_date + timedelta(days=offset))
        by_status = counters.get(d, {})
        reservation_trend.append(
            {
                "date": d,
                "pending": by_status.get("pending", 0),
                "approved": by_status.get("approved", 0),
                "rejected": by_status.get("rejected", 0),
                "cancelled": by_status.get("cancelled", 0),
                "expired": by_status.get("expired", 0),
            }
        )

    # 3) 实验室使用排行：按预约条数倒序取前 8（学生视角即“我最常用的实验室”）。
    usage_query = db.query(Lab.id, Lab.name, func.count(Reservation.id).label("total")).join(
        Reservation, Reservation.lab_id == Lab.id
    )
    if not is_staff:
        usage_query = usage_query.filter(Reservation.user_id == current_user.id)
    lab_usage = [
        {"lab_id": lab_id, "lab_name": name, "count": int(total)}
        for lab_id, name, total in (
            usage_query.group_by(Lab.id, Lab.name).order_by(func.count(Reservation.id).desc()).limit(8).all()
        )
    ]

    # 4) 报修状态分布：pending / processing / resolved。
    repair_query = db.query(Repair.status, func.count(Repair.id))
    if not is_staff:
        repair_query = repair_query.filter(Repair.reporter_id == current_user.id)
    repair_status = [
        {"status": status, "count": int(count)} for status, count in repair_query.group_by(Repair.status).all()
    ]

    return Response.success(
        data={
            "days": days,
            "reservation_trend": reservation_trend,
            "lab_usage": lab_usage,
            "repair_status": repair_status,
        }
    )
