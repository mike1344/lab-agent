from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_staff
from app.models.course import Course, CourseEnrollment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.course import CourseCreate, CourseUpdate, EnrollmentCreate
from app.services.course import find_course_conflict

router = APIRouter(prefix="/courses", tags=["实验课程"])

WEEKDAY_LABELS = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}


def course_to_dict(db: Session, course: Course) -> dict:
    enrolled_count = db.query(CourseEnrollment).filter(CourseEnrollment.course_id == course.id).count()
    return {
        "id": course.id,
        "name": course.name,
        "lab_id": course.lab_id,
        "lab_name": course.lab.name if course.lab else None,
        "teacher_id": course.teacher_id,
        "teacher_name": (course.teacher.full_name or course.teacher.username) if course.teacher else None,
        "weekday": course.weekday,
        "weekday_label": WEEKDAY_LABELS.get(course.weekday, str(course.weekday)),
        "start_time": course.start_time,
        "end_time": course.end_time,
        "start_date": course.start_date,
        "end_date": course.end_date,
        "description": course.description,
        "enrolled_count": enrolled_count,
    }


def _course_query(db: Session):
    return db.query(Course).options(joinedload(Course.lab), joinedload(Course.teacher))


def _ensure_owner_or_admin(course: Course, current_user: User) -> None:
    """课程只能由授课教师本人或管理员维护。"""
    if course.teacher_id != current_user.id and not current_user.is_superuser:
        raise BusinessException(code=BizCode.FORBIDDEN, message="只能管理自己创建的课程")


def _check_conflicts(
    db: Session,
    *,
    lab_id: int,
    weekday: int,
    start_time,
    end_time,
    start_date,
    end_date,
    exclude_course_id: int | None = None,
) -> None:
    """课程落库前统一冲突校验：先查同实验室课表，再查区间内的自由预约。"""
    course_conflict = find_course_conflict(
        db,
        lab_id=lab_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        start_date=start_date,
        end_date=end_date,
        exclude_course_id=exclude_course_id,
    )
    if course_conflict:
        raise BusinessException(code=BizCode.BAD_REQUEST, message=f"该时段已有课程《{course_conflict.name}》占用")

    candidates = (
        db.query(Reservation)
        .filter(
            Reservation.lab_id == lab_id,
            Reservation.status.in_(["pending", "approved"]),
            Reservation.reservation_date >= start_date,
            Reservation.reservation_date <= end_date,
            Reservation.start_time < end_time,
            Reservation.end_time > start_time,
        )
        .all()
    )
    for reservation in candidates:
        # 星期几在数据库间不可移植，取回候选日期后在应用层按周几过滤（课程创建频率低，代价可忽略）
        if reservation.reservation_date.isoweekday() == weekday:
            raise BusinessException(
                code=BizCode.BAD_REQUEST,
                message=f"该时段与已有预约（{reservation.reservation_date}）冲突，请先协调预约",
            )


@router.get("")
def get_courses(
    keyword: str = "",
    lab_id: int | None = None,
    mine: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """课程列表：所有登录用户可看课表；mine=true 只看自己选修的课程。"""
    query = _course_query(db)
    if keyword.strip():
        query = query.filter(Course.name.like(f"%{keyword.strip()}%"))
    if lab_id:
        query = query.filter(Course.lab_id == lab_id)
    if mine:
        query = query.filter(
            Course.id.in_(db.query(CourseEnrollment.course_id).filter(CourseEnrollment.student_id == current_user.id))
        )
    items = query.order_by(Course.start_date.asc(), Course.weekday.asc(), Course.start_time.asc()).all()
    return Response.success(data=[course_to_dict(db, item) for item in items])


@router.get("/available-students")
def get_available_students(
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """选课弹窗的学生候选名单（教师/管理员可用，只暴露必要字段）。"""
    students = (
        db.query(User).filter(User.is_active.is_(True), User.is_superuser.is_(False)).order_by(User.username).all()
    )
    return Response.success(
        data=[
            {"id": item.id, "username": item.username, "full_name": item.full_name, "email": item.email}
            for item in students
        ]
    )


@router.post("")
def create_course(
    data: CourseCreate,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """教师/管理员建课；落库前同时校验课表冲突与已有预约占用。"""
    if not db.get(Lab, data.lab_id):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室不存在")

    teacher_id = current_user.id
    if data.teacher_id is not None:
        if not current_user.is_superuser:
            raise BusinessException(code=BizCode.FORBIDDEN, message="只有管理员可以指定授课教师")
        teacher = db.get(User, data.teacher_id)
        if not teacher:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="授课教师不存在")
        teacher_id = teacher.id

    _check_conflicts(
        db,
        lab_id=data.lab_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    course = Course(
        name=data.name.strip(),
        lab_id=data.lab_id,
        teacher_id=teacher_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
        start_date=data.start_date,
        end_date=data.end_date,
        description=data.description.strip() if data.description else None,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    course = _course_query(db).filter(Course.id == course.id).first()
    return Response.success(message="课程创建成功", data=course_to_dict(db, course))


@router.put("/{course_id}")
def update_course(
    course_id: int,
    data: CourseUpdate,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """修改课程：用「更新后最终值」重新做冲突校验，避免部分更新绕过。"""
    course = _course_query(db).filter(Course.id == course_id).first()
    if not course:
        raise BusinessException(code=BizCode.NOT_FOUND, message="课程不存在")
    _ensure_owner_or_admin(course, current_user)

    update_data = data.model_dump(exclude_unset=True)
    lab_id = update_data.get("lab_id", course.lab_id)
    weekday = update_data.get("weekday", course.weekday)
    start_time = update_data.get("start_time", course.start_time)
    end_time = update_data.get("end_time", course.end_time)
    start_date = update_data.get("start_date", course.start_date)
    end_date = update_data.get("end_date", course.end_date)

    if end_time <= start_time:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="结束时间必须晚于开始时间")
    if end_date < start_date:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="学期结束日期不能早于开始日期")
    if lab_id != course.lab_id and not db.get(Lab, lab_id):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室不存在")

    _check_conflicts(
        db,
        lab_id=lab_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        start_date=start_date,
        end_date=end_date,
        exclude_course_id=course_id,
    )
    for field, value in update_data.items():
        setattr(course, field, value.strip() if field == "name" else value)
    db.commit()
    db.refresh(course)
    course = _course_query(db).filter(Course.id == course.id).first()
    return Response.success(message="课程修改成功", data=course_to_dict(db, course))


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    course = db.get(Course, course_id)
    if not course:
        raise BusinessException(code=BizCode.NOT_FOUND, message="课程不存在")
    _ensure_owner_or_admin(course, current_user)
    # 应用层级联：先清理选课名单再删课程
    db.query(CourseEnrollment).filter(CourseEnrollment.course_id == course_id).delete(synchronize_session=False)
    db.delete(course)
    db.commit()
    return Response.success(message="课程删除成功")


@router.get("/{course_id}/students")
def get_course_students(
    course_id: int,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    course = db.get(Course, course_id)
    if not course:
        raise BusinessException(code=BizCode.NOT_FOUND, message="课程不存在")
    _ensure_owner_or_admin(course, current_user)
    enrollments = (
        db.query(CourseEnrollment)
        .options(joinedload(CourseEnrollment.student))
        .filter(CourseEnrollment.course_id == course_id)
        .order_by(CourseEnrollment.id.asc())
        .all()
    )
    return Response.success(
        data=[
            {
                "student_id": item.student_id,
                "username": item.student.username,
                "full_name": item.student.full_name,
                "email": item.student.email,
            }
            for item in enrollments
        ]
    )


@router.post("/{course_id}/students")
def add_course_students(
    course_id: int,
    data: EnrollmentCreate,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """批量加入选课名单（幂等：已在名单中的学生自动跳过）。"""
    course = db.get(Course, course_id)
    if not course:
        raise BusinessException(code=BizCode.NOT_FOUND, message="课程不存在")
    _ensure_owner_or_admin(course, current_user)

    requested_ids = set(data.student_ids)
    students = db.query(User).filter(User.id.in_(requested_ids), User.is_active.is_(True)).all()
    if len(students) != len(requested_ids):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="选课名单中包含不存在或已禁用的用户")

    existing = {
        item.student_id for item in db.query(CourseEnrollment).filter(CourseEnrollment.course_id == course_id).all()
    }
    added = 0
    for student_id in requested_ids - existing:
        db.add(CourseEnrollment(course_id=course_id, student_id=student_id))
        added += 1
    db.commit()
    return Response.success(message=f"已添加 {added} 名学生", data={"added": added})


@router.delete("/{course_id}/students/{student_id}")
def remove_course_student(
    course_id: int,
    student_id: int,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    course = db.get(Course, course_id)
    if not course:
        raise BusinessException(code=BizCode.NOT_FOUND, message="课程不存在")
    _ensure_owner_or_admin(course, current_user)
    enrollment = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
        .first()
    )
    if not enrollment:
        raise BusinessException(code=BizCode.NOT_FOUND, message="该学生不在选课名单中")
    db.delete(enrollment)
    db.commit()
    return Response.success(message="已移出选课名单")
