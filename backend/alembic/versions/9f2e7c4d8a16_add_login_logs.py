"""新增登录日志表：记录每次登录尝试的用户名、IP、UA 与成败结果。

Revision ID: 9f2e7c4d8a16
Revises: 6cb96b356141
Create Date: 2026-10-21

在 backend 目录下执行：
    alembic upgrade head      # 创建 login_logs 表
    alembic downgrade -1      # 回退：删除 login_logs 表
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f2e7c4d8a16"
down_revision: Union[str, None] = "6cb96b356141"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_logs",
        sa.Column("username", sa.String(length=50), nullable=False, comment="尝试登录的用户名"),
        sa.Column("user_id", sa.Integer(), nullable=True, comment="成功登录时的用户ID"),
        sa.Column("ip", sa.String(length=64), nullable=True, comment="客户端IP"),
        sa.Column("user_agent", sa.String(length=255), nullable=True, comment="浏览器UA"),
        sa.Column("success", sa.Boolean(), nullable=False, comment="是否登录成功"),
        sa.Column("message", sa.String(length=100), nullable=False, comment="结果说明"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="登录日志表",
    )
    op.create_index(op.f("ix_login_logs_id"), "login_logs", ["id"], unique=False)
    op.create_index(op.f("ix_login_logs_username"), "login_logs", ["username"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_login_logs_username"), table_name="login_logs")
    op.drop_index(op.f("ix_login_logs_id"), table_name="login_logs")
    op.drop_table("login_logs")
