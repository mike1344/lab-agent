"""课程冲突判定：课表按周重复占用实验室，与自由预约共用同一套重叠规则。

两条约束：
1. 课程之间：同实验室、同星期几、学期区间有交集、时间段重叠 → 冲突；
2. 课程与预约：预约日期落在课程学期内、星期几匹配、时间段重叠 → 冲突（见 services/reservation.py）。
"""

from datetime import date, time

from sqlalchemy.orm import Session

from app.models.course import Course


def find_course_conflict(
    db: Session,
    *,
    lab_id: int,
    weekday: int,
    start_time: time,
    end_time: time,
    start_date: date,
    end_date: date,
    exclude_course_id: int | None = None,
) -> Course | None:
    """返回与给定课表重叠的第一门课程，None 表示不冲突。"""
    query = db.query(Course).filter(
        Course.lab_id == lab_id,
        Course.weekday == weekday,
        # 学期区间相交
        Course.start_date <= end_date,
        Course.end_date >= start_date,
        # 时间段重叠：[s1,e1) 与 [s2,e2) 相交 ⇔ s1 < e2 且 e1 > s2
        Course.start_time < end_time,
        Course.end_time > start_time,
    )
    if exclude_course_id is not None:
        query = query.filter(Course.id != exclude_course_id)
    return query.first()
