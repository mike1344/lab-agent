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
    # pending / approved / rejected / cancelled / expired
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    review_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 多级审批：创建时快照适用的流程与当前节点；没有配置流程时两个字段均为空，走原来的单级审核。
    approval_flow_id: Mapped[int | None] = mapped_column(
        ForeignKey("approval_flows.id"),
        nullable=True,
        index=True,
        comment="创建时适用的审批流ID",
    )
    approval_step_order: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="当前待审批节点序号；审批完成后保留最后节点便于追溯",
    )

    user = relationship("User")
    lab = relationship("Lab")
    approval_flow = relationship("ApprovalFlow")
    approvals = relationship(
        "ReservationApproval",
        back_populates="reservation",
        cascade="all, delete-orphan",
        order_by="ReservationApproval.step_order",
    )
