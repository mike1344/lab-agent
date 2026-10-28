from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnnouncementRead(Base):
    """公告已读回执：每个用户对每条公告至多一条（create_time 即首次阅读时间）。"""

    __tablename__ = "announcement_reads"
    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_reads_announcement_user"),
        {"comment": "公告已读回执表"},
    )

    announcement_id: Mapped[int] = mapped_column(
        ForeignKey("announcements.id"), nullable=False, index=True, comment="公告ID"
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")

    user = relationship("User")
