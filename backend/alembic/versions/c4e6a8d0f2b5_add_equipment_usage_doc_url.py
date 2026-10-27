"""设备表新增操作说明链接字段。

Revision ID: c4e6a8d0f2b5
Revises: a3d5f7b9c1e2
Create Date: 2026-10-21

在 backend 目录下执行：
    alembic upgrade head      # 新增 equipment.usage_doc_url 列
    alembic downgrade -1      # 回退：删除该列
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e6a8d0f2b5"
down_revision: Union[str, None] = "a3d5f7b9c1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "equipment",
        sa.Column("usage_doc_url", sa.String(length=500), nullable=True, comment="操作说明链接"),
    )


def downgrade() -> None:
    op.drop_column("equipment", "usage_doc_url")
