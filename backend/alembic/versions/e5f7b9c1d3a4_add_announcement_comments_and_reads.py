"""公告评论与已读回执。

Revision ID: e5f7b9c1d3a4
Revises: c4e6a8d0f2b5
Create Date: 2026-10-21

在 backend 目录下执行：
    alembic upgrade head      # 创建 announcement_comments / announcement_reads 表
    alembic downgrade -1      # 回退：删除这两张表
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f7b9c1d3a4"
down_revision: Union[str, None] = "c4e6a8d0f2b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "announcement_comments",
        sa.Column("announcement_id", sa.Integer(), nullable=False, comment="公告ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="评论人ID"),
        sa.Column("parent_id", sa.Integer(), nullable=True, comment="父评论ID（回复）"),
        sa.Column("content", sa.Text(), nullable=False, comment="评论内容"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["announcement_id"],
            ["announcements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["announcement_comments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="公告评论表",
    )
    op.create_index(
        op.f("ix_announcement_comments_announcement_id"), "announcement_comments", ["announcement_id"], unique=False
    )
    op.create_index(op.f("ix_announcement_comments_parent_id"), "announcement_comments", ["parent_id"], unique=False)
    op.create_index(op.f("ix_announcement_comments_user_id"), "announcement_comments", ["user_id"], unique=False)
    op.create_index(op.f("ix_announcement_comments_id"), "announcement_comments", ["id"], unique=False)

    op.create_table(
        "announcement_reads",
        sa.Column("announcement_id", sa.Integer(), nullable=False, comment="公告ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["announcement_id"],
            ["announcements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_reads_announcement_user"),
        comment="公告已读回执表",
    )
    op.create_index(
        op.f("ix_announcement_reads_announcement_id"), "announcement_reads", ["announcement_id"], unique=False
    )
    op.create_index(op.f("ix_announcement_reads_user_id"), "announcement_reads", ["user_id"], unique=False)
    op.create_index(op.f("ix_announcement_reads_id"), "announcement_reads", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_announcement_reads_id"), table_name="announcement_reads")
    op.drop_index(op.f("ix_announcement_reads_user_id"), table_name="announcement_reads")
    op.drop_index(op.f("ix_announcement_reads_announcement_id"), table_name="announcement_reads")
    op.drop_table("announcement_reads")

    op.drop_index(op.f("ix_announcement_comments_id"), table_name="announcement_comments")
    op.drop_index(op.f("ix_announcement_comments_user_id"), table_name="announcement_comments")
    op.drop_index(op.f("ix_announcement_comments_parent_id"), table_name="announcement_comments")
    op.drop_index(op.f("ix_announcement_comments_announcement_id"), table_name="announcement_comments")
    op.drop_table("announcement_comments")
