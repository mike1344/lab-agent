"""新增操作日志表：记录所有写操作的执行人与结果。

Revision ID: a3d5f7b9c1e2
Revises: 9f2e7c4d8a16
Create Date: 2026-10-21

在 backend 目录下执行：
    alembic upgrade head      # 创建 operation_logs 表
    alembic downgrade -1      # 回退：删除 operation_logs 表
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d5f7b9c1e2"
down_revision: Union[str, None] = "9f2e7c4d8a16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operation_logs",
        sa.Column("username", sa.String(length=50), nullable=False, comment="操作人用户名"),
        sa.Column("user_id", sa.Integer(), nullable=True, comment="操作人ID"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, comment="操作时是否管理员"),
        sa.Column("method", sa.String(length=10), nullable=False, comment="HTTP方法"),
        sa.Column("path", sa.String(length=255), nullable=False, comment="请求路径"),
        sa.Column("summary", sa.String(length=100), nullable=False, comment="操作说明"),
        sa.Column("success", sa.Boolean(), nullable=False, comment="是否成功"),
        sa.Column("http_status", sa.Integer(), nullable=False, comment="HTTP状态码"),
        sa.Column("message", sa.String(length=255), nullable=False, comment="结果信息"),
        sa.Column("ip", sa.String(length=64), nullable=True, comment="客户端IP"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, comment="耗时(毫秒)"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="操作日志表",
    )
    op.create_index(op.f("ix_operation_logs_id"), "operation_logs", ["id"], unique=False)
    op.create_index(op.f("ix_operation_logs_user_id"), "operation_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_operation_logs_username"), "operation_logs", ["username"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_operation_logs_username"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_user_id"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_id"), table_name="operation_logs")
    op.drop_table("operation_logs")
