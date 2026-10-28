from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentToolLog(Base):
    """AI 工具调用审计：记录写工具的入参、结果、耗时与幂等键。

    这张表同时承担两个职责：
    1. 审计：谁在什么时候让 AI 执行了什么写操作，结果如何；
    2. 幂等：同一用户 + 同一工具 + 同一参数的重复调用命中 idempotency_key，
       直接返回历史结果，避免模型重试造成重复预约/重复取消。
    """

    __tablename__ = "agent_tool_logs"
    __table_args__ = {"comment": "AI 工具调用审计表"}

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    tool_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="工具名称")
    arguments: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="工具入参 JSON")
    result: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="工具执行结果")
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否执行成功")
    duration_ms: Mapped[int] = mapped_column(nullable=False, default=0, comment="耗时(毫秒)")
    # 只有写工具才有幂等键；唯一约束由数据库兜底并发
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True, comment="写操作幂等键"
    )
    note: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="备注（如等待确认）")
