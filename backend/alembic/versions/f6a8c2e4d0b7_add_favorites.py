"""用户收藏表（实验室 / 设备书签）。

Revision ID: f6a8c2e4d0b7
Revises: e5f7b9c1d3a4
Create Date: 2026-10-21

在 backend 目录下执行：
    alembic upgrade head      # 创建 favorites 表
    alembic downgrade -1      # 回退：删除 favorites 表
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a8c2e4d0b7"
down_revision: Union[str, None] = "e5f7b9c1d3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("target_type", sa.String(length=20), nullable=False, comment="收藏类型：lab/equipment"),
        sa.Column("target_id", sa.Integer(), nullable=False, comment="收藏目标ID"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "target_type", "target_id", name="uq_favorites_user_target"),
        comment="用户收藏表",
    )
    op.create_index(op.f("ix_favorites_id"), "favorites", ["id"], unique=False)
    op.create_index(op.f("ix_favorites_user_id"), "favorites", ["user_id"], unique=False)
    op.create_index(op.f("ix_favorites_target_id"), "favorites", ["target_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_favorites_target_id"), table_name="favorites")
    op.drop_index(op.f("ix_favorites_user_id"), table_name="favorites")
    op.drop_index(op.f("ix_favorites_id"), table_name="favorites")
    op.drop_table("favorites")
