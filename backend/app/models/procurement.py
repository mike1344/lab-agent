from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Procurement(Base):
    """设备采购记录：申请 → 到货 → 验收，验收时自动入库（设备 quantity += quantity）。"""

    __tablename__ = "procurements"
    __table_args__ = {"comment": "设备采购记录表"}

    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment.id"), nullable=True, index=True, comment="关联设备ID（验收时必填）"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="采购物品名称")
    quantity: Mapped[int] = mapped_column(default=1, nullable=False, comment="采购数量")
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="申请人ID")
    # pending 申请中 / arrived 已到货 / accepted 已验收（验收后库存入库且记录不可删除）
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="状态：pending/arrived/accepted"
    )
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")

    equipment = relationship("Equipment")
    applicant = relationship("User")
