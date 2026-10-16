from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notification(Base):
    """站内通知：审核结果、预约提醒、报修进度等。"""

    __tablename__ = "notifications"
    __table_args__ = {"comment": "站内通知表"}

    # 接收人 ID
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="接收人ID")
    # 通知类型：reservation_result 审核结果 / reservation_reminder 预约提醒 / repair_result 报修进度 / system 系统通知
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="system", index=True, comment="通知类型")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="通知标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="通知内容")
    # 是否已读
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否已读")
    # 关联业务 ID（如预约 ID），点击可跳转对应页面
    related_id: Mapped[int | None] = mapped_column(nullable=True, comment="关联业务ID")

    user = relationship("User")
