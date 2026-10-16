from datetime import date, time

from sqlalchemy import Date, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Reservation(Base):
    """学生提交的实验室预约申请。"""

    __tablename__ = "reservations"
    __table_args__ = {"comment": "实验室预约表"}

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True)
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    # pending / approved / rejected / cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    review_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user = relationship("User")
    lab = relationship("Lab")
