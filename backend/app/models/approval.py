"""多级审批流：实验室可配置多步审批，预约按节点逐级流转。"""

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApprovalFlow(Base):
    """实验室预约审批流：一个实验室最多配置一条启用中的流程。"""

    __tablename__ = "approval_flows"
    __table_args__ = {"comment": "预约审批流表"}

    lab_id: Mapped[int] = mapped_column(
        ForeignKey("labs.id"),
        unique=True,
        nullable=False,
        index=True,
        comment="适用实验室ID，一个实验室一条流程",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="流程名称")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="流程说明")
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用：停用后新预约不再进入本流程，进行中的预约继续走完",
    )

    lab = relationship("Lab")
    steps = relationship(
        "ApprovalStep",
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="ApprovalStep.step_order",
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<ApprovalFlow id={self.id} lab_id={self.lab_id} name={self.name!r}>"


class ApprovalStep(Base):
    """审批流的单个节点：按角色（管理员/教师）或指定人员审批。"""

    __tablename__ = "approval_steps"
    __table_args__ = (
        UniqueConstraint("flow_id", "step_order", name="uq_approval_steps_flow_order"),
        {"comment": "审批流节点表"},
    )

    flow_id: Mapped[int] = mapped_column(ForeignKey("approval_flows.id"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(nullable=False, comment="节点顺序，从 1 开始")
    name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="节点名称，如“导师初审”")
    # role：按角色匹配审批人；user：指定某位教师/管理员
    approver_type: Mapped[str] = mapped_column(String(20), default="role", nullable=False, comment="审批人类型")
    approver_role: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="角色审批时的角色：admin / teacher",
    )
    approver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="指定人员审批时的用户ID",
    )

    flow = relationship("ApprovalFlow", back_populates="steps")
    approver = relationship("User")

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<ApprovalStep flow_id={self.flow_id} order={self.step_order} type={self.approver_type}>"


class ReservationApproval(Base):
    """预约的审批轨迹：每一步谁在什么时候通过/拒绝了，作为不可改写的审计记录。"""

    __tablename__ = "reservation_approvals"
    __table_args__ = (
        UniqueConstraint("reservation_id", "step_order", name="uq_reservation_approvals_reservation_step"),
        {"comment": "预约审批轨迹表"},
    )

    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(nullable=False, comment="审批节点顺序")
    step_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="节点名称快照")
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False, comment="approve / reject")
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="审批意见")

    reservation = relationship("Reservation", back_populates="approvals")
    approver = relationship("User")

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return (
            f"<ReservationApproval reservation_id={self.reservation_id} step={self.step_order} action={self.action!r}>"
        )
