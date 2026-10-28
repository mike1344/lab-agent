"""检查示例数据是否导入成功（在 backend 目录执行）。

.\\.venv\\Scripts\\python.exe scripts\\verify_seed.py
"""

import sys
from pathlib import Path

# 允许从 backend 目录直接运行：把 backend 加入模块搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import engine  # noqa: E402
from sqlalchemy import text  # noqa: E402

QUERIES = [
    ("用户总数", "SELECT COUNT(*) FROM users"),
    ("学生", "SELECT COUNT(*) FROM users WHERE username LIKE 'pku_cs2401_%'"),
    ("教师", "SELECT COUNT(*) FROM users WHERE username LIKE 'pku_teacher_%'"),
    ("实验室", "SELECT COUNT(*) FROM labs"),
    ("设备", "SELECT COUNT(*) FROM equipment WHERE code LIKE 'PKU-CS-%'"),
    ("课程", "SELECT COUNT(*) FROM courses"),
    ("选课", "SELECT COUNT(*) FROM course_enrollments"),
    ("预约总数", "SELECT COUNT(*) FROM reservations"),
    ("预约-已通过", "SELECT COUNT(*) FROM reservations WHERE status = 'approved'"),
    ("预约-待审核", "SELECT COUNT(*) FROM reservations WHERE status = 'pending'"),
]

with engine.connect() as connection:
    for label, sql in QUERIES:
        print(f"{label}: {connection.execute(text(sql)).scalar()}")
    print("\n--- 实验室（全部） ---")
    for row in connection.execute(text("SELECT id, name FROM labs ORDER BY id")):
        print(row)
    print("\n--- pku 用户 ---")
    for row in connection.execute(
        text("SELECT username, full_name, is_teacher FROM users WHERE username LIKE 'pku_%' ORDER BY username")
    ):
        print(row)
    print("\n--- 预约样例（最近 5 条） ---")
    for row in connection.execute(
        text(
            "SELECT r.reservation_date, r.start_time, r.status, u.full_name, l.name "
            "FROM reservations r "
            "JOIN users u ON u.id = r.user_id "
            "JOIN labs l ON l.id = r.lab_id "
            "ORDER BY r.id DESC LIMIT 5"
        )
    ):
        print(row)

    print("\n--- 数据一致性校验（仅示例数据） ---")
    overlap = connection.execute(
        text(
            "SELECT COUNT(*) FROM reservations r1 "
            "JOIN reservations r2 ON r1.id < r2.id "
            "AND r1.lab_id = r2.lab_id AND r1.reservation_date = r2.reservation_date "
            "AND r1.start_time < r2.end_time AND r1.end_time > r2.start_time "
            "AND r1.status IN ('pending','approved') AND r2.status IN ('pending','approved') "
            "WHERE r1.purpose LIKE '%PKU 示例数据%' AND r2.purpose LIKE '%PKU 示例数据%'"
        )
    ).scalar()
    print(f"实验室同时段冲突（应为 0）：{overlap}")

    quota_violations = connection.execute(
        text(
            "SELECT COUNT(*) FROM ("
            "  SELECT u.username, YEARWEEK(r.reservation_date, 3) AS wk, COUNT(*) AS cnt "
            "  FROM reservations r JOIN users u ON u.id = r.user_id "
            "  WHERE r.purpose LIKE '%PKU 示例数据%' AND r.status IN ('pending','approved') "
            "  GROUP BY u.username, wk HAVING cnt > 3"
            ") AS t"
        )
    ).scalar()
    print(f"学生每周超过 3 条（应为 0）：{quota_violations}")

    past = connection.execute(
        text("SELECT COUNT(*) FROM reservations WHERE purpose LIKE '%PKU 示例数据%' AND reservation_date < CURDATE()")
    ).scalar()
    print(f"落在过去的预约（应为 0）：{past}")
