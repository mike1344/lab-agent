from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Equipment(Base):
    """实验室设备信息。"""

    __tablename__ = "equipment"
    __table_args__ = {"comment": "实验室设备表"}

    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 1 表示正常，0 表示停用或维护中。
    status: Mapped[int] = mapped_column(default=1, nullable=False)

    lab = relationship("Lab")
