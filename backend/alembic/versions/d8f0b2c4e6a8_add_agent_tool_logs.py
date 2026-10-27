"""AI 工具调用审计表。

Revision ID: d8f0b2c4e6a8
Revises: b1d3f5a7c9e2
Create Date: 2026-10-27

在 backend 目录下执行：
    alembic upgrade head      # 创建 agent_tool_logs 表
    alembic downgrade -1      # 回退：删除 agent_tool_logs 表
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8f0b2c4e6a8"
down_revision: Union[str, None] = "b1d3f5a7c9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_tool_logs",
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("tool_name", sa.String(length=50), nullable=False, comment="工具名称"),
        sa.Column("arguments", sa.Text(), nullable=False, comment="工具入参 JSON"),
        sa.Column("result", sa.Text(), nullable=False, comment="工具执行结果"),
        sa.Column("success", sa.Boolean(), nullable=False, comment="是否执行成功"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, comment="耗时(毫秒)"),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True, comment="写操作幂等键"),
        sa.Column("note", sa.String(length=100), nullable=False, comment="备注（如等待确认）"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_agent_tool_logs_idempotency_key"),
        comment="AI 工具调用审计表",
    )
    op.create_index(op.f("ix_agent_tool_logs_id"), "agent_tool_logs", ["id"], unique=False)
    op.create_index(op.f("ix_agent_tool_logs_user_id"), "agent_tool_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_agent_tool_logs_tool_name"), "agent_tool_logs", ["tool_name"], unique=False)
    op.create_index(op.f("ix_agent_tool_logs_idempotency_key"), "agent_tool_logs", ["idempotency_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_tool_logs_idempotency_key"), table_name="agent_tool_logs")
    op.drop_index(op.f("ix_agent_tool_logs_tool_name"), table_name="agent_tool_logs")
    op.drop_index(op.f("ix_agent_tool_logs_user_id"), table_name="agent_tool_logs")
    op.drop_index(op.f("ix_agent_tool_logs_id"), table_name="agent_tool_logs")
    op.drop_table("agent_tool_logs")
