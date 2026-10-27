from datetime import date, time

from sqlalchemy import Date, ForeignKey, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Course(Base):
    """实验课程：按周重复的固定课表，占用实验室时段。"""

    __tablename__ = "courses"
    __table_args__ = {"comment": "实验课程表"}

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="课程名称")
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True, comment="实验室ID")
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="授课教师ID")
    # 1=周一 ... 7=周日（与 Python date.isoweekday() 对齐）
    weekday: Mapped[int] = mapped_column(nullable=False, comment="周几（1-7）")
    start_time: Mapped[time] = mapped_column(Time, nullable=False, comment="开始时间")
    end_time: Mapped[time] = mapped_column(Time, nullable=False, comment="结束时间")
    start_date: Mapped[date] = mapped_column(Date, nullable=False, comment="学期开始日期")
    end_date: Mapped[date] = mapped_column(Date, nullable=False, comment="学期结束日期")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="课程说明")

    lab = relationship("Lab")
    teacher = relationship("User")


class CourseEnrollment(Base):
    """选课名单：每个学生在一门课中至多一条记录。"""

    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_course_enrollments_course_student"),
        {"comment": "课程选课名单表"},
    )

    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True, comment="课程ID")
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, comment="学生ID")

    student = relationship("User")
