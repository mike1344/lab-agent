from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.equipment import Equipment
from app.models.lab import Lab
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
        "equipment_count": db.query(func.coalesce(func.sum(Equipment.quantity), 0)).filter(
            Equipment.status == 1
        ).scalar() or 0,
        "reservation_count": reservation_query.scalar() or 0,
        "pending_count": pending_query.scalar() or 0,
    }
    if current_user.is_superuser:
        data["user_count"] = db.query(func.count(User.id)).scalar() or 0
    return Response.success(data=data)
