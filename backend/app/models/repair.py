from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Repair(Base):
    """实验室/设备报修记录。学生提交，管理员处理。"""

    __tablename__ = "repairs"
    __table_args__ = {"comment": "报修记录表"}

    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="报修人ID")
    lab_id: Mapped[int | None] = mapped_column(ForeignKey("labs.id"), nullable=True, index=True, comment="关联实验室ID")
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment.id"), nullable=True, index=True, comment="关联设备ID"
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="报修标题")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="故障描述")
    # pending / processing / resolved
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True, comment="处理状态")
    handle_comment: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="处理备注")
    handler_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, comment="处理人ID")

    reporter = relationship("User", foreign_keys=[reporter_id])
    handler = relationship("User", foreign_keys=[handler_id])
    lab = relationship("Lab")
    equipment = relationship("Equipment")
