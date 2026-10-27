from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnnouncementComment(Base):
    """公告评论：parent_id 指向同公告下的顶级评论，实现一层回复。"""

    __tablename__ = "announcement_comments"
    __table_args__ = {"comment": "公告评论表"}

    announcement_id: Mapped[int] = mapped_column(
        ForeignKey("announcements.id"), nullable=False, index=True, comment="公告ID"
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="评论人ID")
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("announcement_comments.id"), nullable=True, index=True, comment="父评论ID（回复）"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评论内容")

    user = relationship("User")
