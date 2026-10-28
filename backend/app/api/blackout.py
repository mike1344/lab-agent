from datetime import date, time

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.blackout import BlackoutPeriod
from app.models.user import User

router = APIRouter(prefix="/blackouts", tags=["不可约时段"])


class BlackoutCreate(BaseModel):
    lab_id: int
    blackout_date: date
    start_time: str = Field(pattern=r"^\d{2}:\d{2}(:\d{2})?$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}(:\d{2})?$")
    reason: str = Field(min_length=2, max_length=200)


@router.get("")
def list_blackouts(
    lab_id: int | None = None,
    blackout_date: date | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询不可约时段（学生和管理员都能查，前端时间轴用）。"""
    query = db.query(BlackoutPeriod)
    if lab_id:
        query = query.filter(BlackoutPeriod.lab_id == lab_id)
    if blackout_date:
        query = query.filter(BlackoutPeriod.blackout_date == blackout_date)
    items = query.order_by(BlackoutPeriod.blackout_date, BlackoutPeriod.start_time).all()
    return Response.success(
        data=[
            {
                "id": b.id,
                "lab_id": b.lab_id,
                "blackout_date": str(b.blackout_date),
                "start_time": str(b.start_time),
                "end_time": str(b.end_time),
                "reason": b.reason,
            }
            for b in items
        ]
    )


@router.post("")
def create_blackout(
    data: BlackoutCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员设置不可约时段。"""
    # 显式转成 time 对象再入库：不依赖数据库驱动的隐式字符串转换（SQLite 下会直接拒绝）。
    start = time.fromisoformat(data.start_time)
    end = time.fromisoformat(data.end_time)
    if start >= end:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="结束时间必须晚于开始时间")
    b = BlackoutPeriod(
        lab_id=data.lab_id,
        blackout_date=data.blackout_date,
        start_time=start,
        end_time=end,
        reason=data.reason,
    )
    db.add(b)
    db.commit()
    return Response.success(message="已设置不可约时段")


@router.delete("/{blackout_id}")
def delete_blackout(
    blackout_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员删除不可约时段。"""
    b = db.get(BlackoutPeriod, blackout_id)
    if not b:
        raise BusinessException(code=BizCode.NOT_FOUND, message="记录不存在")
    db.delete(b)
    db.commit()
    return Response.success(message="已删除")
