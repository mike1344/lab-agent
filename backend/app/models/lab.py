from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lab(Base):
    """实验室基础信息。"""

    __tablename__ = "labs"
    __table_args__ = {"comment": "实验室表"}

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 1 表示开放预约，0 表示暂停使用。
    status: Mapped[int] = mapped_column(default=1, nullable=False)
