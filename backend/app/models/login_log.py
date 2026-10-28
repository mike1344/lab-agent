from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LoginLog(Base):
    """登录日志：成功与失败都记录，用于安全审计与锁定问题排查。"""

    __tablename__ = "login_logs"
    __table_args__ = {"comment": "登录日志表"}

    # 尝试登录的用户名（可能是任意输入，因此不与 users 表强关联）
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="尝试登录的用户名")
    # 登录成功时记录用户 ID，失败（或用户不存在）时为空
    user_id: Mapped[int | None] = mapped_column(nullable=True, comment="成功登录时的用户ID")
    # 客户端来源信息，取自请求头
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="客户端IP")
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="浏览器UA")
    # 本次尝试的结果
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否登录成功")
    message: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="结果说明")
