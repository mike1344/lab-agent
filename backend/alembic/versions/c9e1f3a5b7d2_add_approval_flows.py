"""多级审批流：流程、节点、预约审批轨迹。

Revision ID: c9e1f3a5b7d2
Revises: d8f0b2c4e6a8
Create Date: 2026-10-28

在 backend 目录下执行：
    alembic upgrade head      # 创建 approval_flows / approval_steps / reservation_approvals，并给 reservations 加两列
    alembic downgrade -1      # 回退：删除新增表与两列
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e1f3a5b7d2"
down_revision: Union[str, None] = "d8f0b2c4e6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_flows",
        sa.Column("lab_id", sa.Integer(), nullable=False, comment="适用实验室ID，一个实验室一条流程"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="流程名称"),
        sa.Column("description", sa.String(length=500), nullable=True, comment="流程说明"),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False, comment="是否启用"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="预约审批流表",
    )
    op.create_index(op.f("ix_approval_flows_id"), "approval_flows", ["id"], unique=False)
    op.create_index(op.f("ix_approval_flows_lab_id"), "approval_flows", ["lab_id"], unique=True)

    op.create_table(
        "approval_steps",
        sa.Column("flow_id", sa.Integer(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False, comment="节点顺序，从 1 开始"),
        sa.Column("name", sa.String(length=100), nullable=True, comment="节点名称，如“导师初审”"),
        sa.Column(
            "approver_type",
            sa.String(length=20),
            server_default="role",
            nullable=False,
            comment="审批人类型：role / user",
        ),
        sa.Column("approver_role", sa.String(length=20), nullable=True, comment="角色审批时的角色"),
        sa.Column("approver_id", sa.Integer(), nullable=True, comment="指定人员审批时的用户ID"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["flow_id"], ["approval_flows.id"]),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flow_id", "step_order", name="uq_approval_steps_flow_order"),
        comment="审批流节点表",
    )
    op.create_index(op.f("ix_approval_steps_id"), "approval_steps", ["id"], unique=False)
    op.create_index(op.f("ix_approval_steps_flow_id"), "approval_steps", ["flow_id"], unique=False)
    op.create_index(op.f("ix_approval_steps_approver_id"), "approval_steps", ["approver_id"], unique=False)

    with op.batch_alter_table("reservations") as batch_op:
        batch_op.add_column(sa.Column("approval_flow_id", sa.Integer(), nullable=True, comment="创建时适用的审批流ID"))
        batch_op.add_column(sa.Column("approval_step_order", sa.Integer(), nullable=True, comment="当前待审批节点序号"))
        batch_op.create_index(op.f("ix_reservations_approval_flow_id"), ["approval_flow_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_reservations_approval_flow_id",
            "approval_flows",
            ["approval_flow_id"],
            ["id"],
        )

    op.create_table(
        "reservation_approvals",
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False, comment="审批节点顺序"),
        sa.Column("step_name", sa.String(length=100), nullable=False, comment="节点名称快照"),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False, comment="approve / reject"),
        sa.Column("comment", sa.String(length=500), nullable=True, comment="审批意见"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"]),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id", "step_order", name="uq_reservation_approvals_reservation_step"),
        comment="预约审批轨迹表",
    )
    op.create_index(op.f("ix_reservation_approvals_id"), "reservation_approvals", ["id"], unique=False)
    op.create_index(
        op.f("ix_reservation_approvals_reservation_id"),
        "reservation_approvals",
        ["reservation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reservation_approvals_approver_id"),
        "reservation_approvals",
        ["approver_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reservation_approvals_approver_id"), table_name="reservation_approvals")
    op.drop_index(op.f("ix_reservation_approvals_reservation_id"), table_name="reservation_approvals")
    op.drop_index(op.f("ix_reservation_approvals_id"), table_name="reservation_approvals")
    op.drop_table("reservation_approvals")

    with op.batch_alter_table("reservations") as batch_op:
        batch_op.drop_constraint("fk_reservations_approval_flow_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_reservations_approval_flow_id"))
        batch_op.drop_column("approval_step_order")
        batch_op.drop_column("approval_flow_id")

    op.drop_index(op.f("ix_approval_steps_approver_id"), table_name="approval_steps")
    op.drop_index(op.f("ix_approval_steps_flow_id"), table_name="approval_steps")
    op.drop_index(op.f("ix_approval_steps_id"), table_name="approval_steps")
    op.drop_table("approval_steps")

    op.drop_index(op.f("ix_approval_flows_lab_id"), table_name="approval_flows")
    op.drop_index(op.f("ix_approval_flows_id"), table_name="approval_flows")
    op.drop_table("approval_flows")
