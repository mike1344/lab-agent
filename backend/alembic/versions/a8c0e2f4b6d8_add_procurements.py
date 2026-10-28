"""设备采购记录表。

Revision ID: a8c0e2f4b6d8
Revises: f6a8c2e4d0b7
Create Date: 2026-10-21

在 backend 目录下执行：
    alembic upgrade head      # 创建 procurements 表
    alembic downgrade -1      # 回退：删除 procurements 表
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8c0e2f4b6d8"
down_revision: Union[str, None] = "f6a8c2e4d0b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "procurements",
        sa.Column("equipment_id", sa.Integer(), nullable=True, comment="关联设备ID（验收时必填）"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="采购物品名称"),
        sa.Column("quantity", sa.Integer(), nullable=False, comment="采购数量"),
        sa.Column("applicant_id", sa.Integer(), nullable=False, comment="申请人ID"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="状态：pending/arrived/accepted"),
        sa.Column("remark", sa.String(length=255), nullable=True, comment="备注"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
        ),
        sa.ForeignKeyConstraint(
            ["applicant_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="设备采购记录表",
    )
    op.create_index(op.f("ix_procurements_id"), "procurements", ["id"], unique=False)
    op.create_index(op.f("ix_procurements_equipment_id"), "procurements", ["equipment_id"], unique=False)
    op.create_index(op.f("ix_procurements_applicant_id"), "procurements", ["applicant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_procurements_applicant_id"), table_name="procurements")
    op.drop_index(op.f("ix_procurements_equipment_id"), table_name="procurements")
    op.drop_index(op.f("ix_procurements_id"), table_name="procurements")
    op.drop_table("procurements")
