from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Favorite(Base):
    """用户收藏：target_type 取值 lab / equipment，target_id 指向对应表主键。"""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_favorites_user_target"),
        {"comment": "用户收藏表"},
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="收藏类型：lab/equipment")
    target_id: Mapped[int] = mapped_column(nullable=False, index=True, comment="收藏目标ID")
