from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OperationLog(Base):
    """操作日志：记录所有写操作（谁、何时、对哪个接口做了什么、结果如何）。"""

    __tablename__ = "operation_logs"
    __table_args__ = {"comment": "操作日志表"}

    # 操作人信息：登录凭证解析失败时 username 记录占位符（如“(未登录)”）
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="操作人用户名")
    user_id: Mapped[int | None] = mapped_column(nullable=True, index=True, comment="操作人ID")
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="操作时是否管理员")
    # 请求信息
    method: Mapped[str] = mapped_column(String(10), nullable=False, comment="HTTP方法")
    path: Mapped[str] = mapped_column(String(255), nullable=False, comment="请求路径")
    summary: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="操作说明")
    # 结果信息
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否成功")
    http_status: Mapped[int] = mapped_column(nullable=False, default=200, comment="HTTP状态码")
    message: Mapped[str] = mapped_column(String(255), nullable=False, default="", comment="结果信息")
    # 来源与耗时
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="客户端IP")
    duration_ms: Mapped[int] = mapped_column(nullable=False, default=0, comment="耗时(毫秒)")
