"""为浏览器 E2E 验收准备固定账号、实验室和一条待审核预约（幂等）。

不依赖 HTTP，也不修改其他实验室的数据；重复执行会重置 E2E 实验室的预约。
用法（backend 目录）：
    .\\.venv\\Scripts\\python.exe scripts\\seed_e2e.py
"""

import sys
from datetime import date, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.approval import ApprovalFlow, ReservationApproval  # noqa: E402
from app.models.lab import Lab  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.reservation import Reservation  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.password import hash_password  # noqa: E402

USERS = [
    ("e2e_admin", "E2eAdmin123!", "E2E 管理员", "e2e_admin@example.com", True, False),
    ("e2e_teacher", "E2eTeacher123!", "E2E 教师", "e2e_teacher@example.com", False, True),
    ("e2e_student", "E2eStudent123!", "E2E 学生", "e2e_student@example.com", False, False),
]
LAB_NAME = "E2E 演示实验室"


def main() -> None:
    db = SessionLocal()
    try:
        users: dict[str, User] = {}
        for username, password, full_name, email, is_admin, is_teacher in USERS:
            user = db.query(User).filter(User.username == username).first()
            if user is None:
                user = User(username=username, email=email, full_name=full_name)
                db.add(user)
            user.password = hash_password(password)
            user.email = email
            user.full_name = full_name
            user.is_active = True
            user.is_superuser = is_admin
            user.is_teacher = is_teacher
            users[username] = user

        lab = db.query(Lab).filter(Lab.name == LAB_NAME).first()
        if lab is None:
            lab = Lab(name=LAB_NAME, location="实训楼 E2E", capacity=10, description="浏览器端到端验收专用")
            db.add(lab)
        lab.location = "实训楼 E2E"
        lab.capacity = 10
        lab.status = 1
        db.flush()

        # 先清掉 E2E 实验室的历史预约，再删审批流，避免预约还引用流程时外键失败。
        old_ids = [item.id for item in db.query(Reservation.id).filter(Reservation.lab_id == lab.id).all()]
        if old_ids:
            db.query(ReservationApproval).filter(ReservationApproval.reservation_id.in_(old_ids)).delete(
                synchronize_session=False
            )
            db.query(Notification).filter(Notification.related_id.in_(old_ids)).delete(synchronize_session=False)
            db.query(Reservation).filter(Reservation.id.in_(old_ids)).delete(synchronize_session=False)

        # E2E 场景固定走单级教师审核，避免开发库里遗留的审批流影响断言。
        flow = db.query(ApprovalFlow).filter(ApprovalFlow.lab_id == lab.id).first()
        if flow is not None:
            db.delete(flow)
            db.flush()

        tomorrow = date.today() + timedelta(days=1)
        reservation = Reservation(
            user_id=users["e2e_student"].id,
            lab_id=lab.id,
            reservation_date=tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            purpose="E2E 验收：预约创建与教师审核",
            status="pending",
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)

        print("E2E 数据已就绪")
        print(f"  学生：e2e_student / E2eStudent123!（预约 ID={reservation.id}，{tomorrow} 09:00-10:00）")
        print("  教师：e2e_teacher / E2eTeacher123!")
        print("  管理员：e2e_admin / E2eAdmin123!")
        print(f"  实验室：{LAB_NAME}（ID={lab.id}）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
