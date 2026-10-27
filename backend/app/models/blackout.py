from datetime import date, time

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BlackoutPeriod(Base):
    """实验室不可预约时段：维护、节假日、考试等临时封闭时间。"""

    __tablename__ = "blackout_periods"
    __table_args__ = {"comment": "实验室不可约时段表"}

    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True, comment="实验室ID")
    blackout_date: Mapped[date] = mapped_column(nullable=False, index=True, comment="不可约日期")
    start_time: Mapped[time] = mapped_column(nullable=False, comment="不可约开始时间")
    end_time: Mapped[time] = mapped_column(nullable=False, comment="不可约结束时间")
    reason: Mapped[str] = mapped_column(String(200), nullable=False, comment="原因")

    lab = relationship("Lab")
