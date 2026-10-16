from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Announcement(Base):
    """系统公告，由管理员发布，所有登录用户可见。"""

    __tablename__ = "announcements"
    __table_args__ = {"comment": "系统公告表"}

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="公告标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="公告内容")
    # 是否置顶：置顶公告在列表中优先展示
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否置顶")
    # 发布者 ID，关联用户表
    publisher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="发布者ID")

    publisher = relationship("User")
