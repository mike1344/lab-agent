"""实验课程与选课名单。

Revision ID: b1d3f5a7c9e2
Revises: a8c0e2f4b6d8
Create Date: 2026-10-21

在 backend 目录下执行：
    alembic upgrade head      # 创建 courses / course_enrollments 表
    alembic downgrade -1      # 回退：删除这两张表
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1d3f5a7c9e2"
down_revision: Union[str, None] = "a8c0e2f4b6d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("name", sa.String(length=100), nullable=False, comment="课程名称"),
        sa.Column("lab_id", sa.Integer(), nullable=False, comment="实验室ID"),
        sa.Column("teacher_id", sa.Integer(), nullable=False, comment="授课教师ID"),
        sa.Column("weekday", sa.Integer(), nullable=False, comment="周几（1-7）"),
        sa.Column("start_time", sa.Time(), nullable=False, comment="开始时间"),
        sa.Column("end_time", sa.Time(), nullable=False, comment="结束时间"),
        sa.Column("start_date", sa.Date(), nullable=False, comment="学期开始日期"),
        sa.Column("end_date", sa.Date(), nullable=False, comment="学期结束日期"),
        sa.Column("description", sa.Text(), nullable=True, comment="课程说明"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["lab_id"],
            ["labs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="实验课程表",
    )
    op.create_index(op.f("ix_courses_id"), "courses", ["id"], unique=False)
    op.create_index(op.f("ix_courses_lab_id"), "courses", ["lab_id"], unique=False)
    op.create_index(op.f("ix_courses_teacher_id"), "courses", ["teacher_id"], unique=False)

    op.create_table(
        "course_enrollments",
        sa.Column("course_id", sa.Integer(), nullable=False, comment="课程ID"),
        sa.Column("student_id", sa.Integer(), nullable=False, comment="学生ID"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("create_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "student_id", name="uq_course_enrollments_course_student"),
        comment="课程选课名单表",
    )
    op.create_index(op.f("ix_course_enrollments_id"), "course_enrollments", ["id"], unique=False)
    op.create_index(op.f("ix_course_enrollments_course_id"), "course_enrollments", ["course_id"], unique=False)
    op.create_index(op.f("ix_course_enrollments_student_id"), "course_enrollments", ["student_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_course_enrollments_student_id"), table_name="course_enrollments")
    op.drop_index(op.f("ix_course_enrollments_course_id"), table_name="course_enrollments")
    op.drop_index(op.f("ix_course_enrollments_id"), table_name="course_enrollments")
    op.drop_table("course_enrollments")

    op.drop_index(op.f("ix_courses_teacher_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_lab_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_id"), table_name="courses")
    op.drop_table("courses")
