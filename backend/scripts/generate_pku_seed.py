"""生成「北京大学计算机系」风格的示例数据 SQL，并可直接写入当前数据库。

生成内容：
- 8 个实验室（计算机系常见方向命名）
- 每室 3 台设备（共 24 台）
- 2 名教师 + 18 名学生（密码见文件头注释）
- 2 门实验课程 + 选课名单
- 约 100 条预约（约 6 成已通过、4 成待审核，分散在未来 12 天、避开课程时段）
- 幂等：用户/实验室/设备/选课用 INSERT IGNORE 或 NOT EXISTS 防重复；预约带幂等条件

用法（在 backend 目录执行）：
    # 只生成 SQL 文件（给 Navicat 用）
    .\\.venv\\Scripts\\python.exe scripts\\generate_pku_seed.py

    # 生成并直接写入当前数据库（读取 backend/.env 的 DATABASE_URL）
    .\\.venv\\Scripts\\python.exe scripts\\generate_pku_seed.py --execute
"""

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# 允许从 backend 目录直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.password import hash_password  # noqa: E402

OUTPUT = Path(__file__).resolve().parent / "seed_pku_cs.sql"

LABS = [
    ("计算机系统与体系结构实验室", "理科一号楼 1801", 30, "体系结构、编译与操作系统课程实验"),
    ("网络与信息安全实验室", "理科一号楼 1812", 28, "网络攻防、密码学与安全协议实验"),
    ("人工智能与机器学习实验室", "理科二号楼 2736", 32, "机器学习、深度学习与大模型研究"),
    ("视觉与听觉信息处理实验室", "理科二号楼 2601", 24, "计算机视觉、语音与多模态感知"),
    ("数据库与数据管理实验室", "理科一号楼 1702", 20, "数据库内核、查询优化与数据系统"),
    ("软件工程与人机交互实验室", "方李邦琴楼 B101", 36, "软件工程、交互设计与可用性测试"),
    ("图形学与虚拟现实实验室", "理科二号楼 2810", 22, "图形渲染、动作捕捉与 VR 实验"),
    ("高性能计算与系统软件实验室", "理科一号楼 1903", 18, "并行计算、分布式系统与系统软件"),
]

EQUIPMENT = [
    ("GPU 工作站（RTX 4090）", "GPU", "显卡服务器，供深度学习实验使用"),
    ("刀片服务器（双路）", "SERVER", "虚拟化与分布式实验节点"),
    ("千兆实验交换机", "NET", "网络实验拓扑核心设备"),
    ("FPGA 实验板卡", "FPGA", "体系结构与硬件实验"),
    ("动作捕捉摄像头组", "MOCAP", "图形学与 VR 实验"),
    ("网络靶场机柜", "LAB", "安全攻防演练环境"),
]

TEACHERS = [
    ("pku_teacher_li", "李文博", "liwenbo@pku.edu.cn", "计算机系统结构实验"),
    ("pku_teacher_wang", "王思远", "wangsiyuan@pku.edu.cn", "网络攻防实践"),
]

STUDENT_NAMES = [
    "陈思远",
    "林晓彤",
    "王一诺",
    "赵子涵",
    "刘雨桐",
    "周子墨",
    "吴嘉懿",
    "郑皓轩",
    "孙可欣",
    "马宇辰",
    "朱雨萱",
    "胡明哲",
    "郭若曦",
    "何俊熙",
    "高梓涵",
    "罗晨曦",
    "梁以宁",
    "宋知远",
]

COURSES = [
    {
        "name": "计算机系统结构实验",
        "lab": "计算机系统与体系结构实验室",
        "teacher": "pku_teacher_li",
        "weekday": 3,
        "start": "08:00:00",
        "end": "10:00:00",
    },
    {
        "name": "网络攻防实践",
        "lab": "网络与信息安全实验室",
        "teacher": "pku_teacher_wang",
        "weekday": 4,
        "start": "10:00:00",
        "end": "12:00:00",
    },
]

# 预约时段避开课程时段（课程在 08:00-12:00），每天两个时段
RESERVATION_SLOTS = [("14:00:00", "15:00:00"), ("15:30:00", "16:30:00"), ("17:00:00", "18:00:00")]
PURPOSES = [
    "课程实验（数据结构）",
    "科研项目实验",
    "学科竞赛训练",
    "毕业设计实验",
    "助教答疑与自习",
]


def sql_str(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def build_sql() -> str:
    rng = random.Random(20261021)
    student_password = hash_password("Student123456")
    teacher_password = hash_password("Teacher123456")
    lines: list[str] = []
    add = lines.append

    add("-- ============================================================")
    add("-- 北京大学计算机系示例数据（自动生成，可直接在 Navicat 运行）")
    add("-- 学生账号：pku_cs2401_01 .. pku_cs2401_18  密码：Student123456")
    add("-- 教师账号：pku_teacher_li / pku_teacher_wang  密码：Teacher123456")
    add("-- 预约：约 100 条，6 成已通过、4 成待审核，分布在未来 12 天")
    add("-- 清理语句见文件末尾；重复执行不会重复插入用户/实验室/设备/选课/预约")
    add("-- ============================================================")
    add("SET NAMES utf8mb4;")
    add("")

    # 教师
    add("-- 教师")
    for username, full_name, email, _course in TEACHERS:
        add(
            "INSERT IGNORE INTO users (username, password, email, full_name, is_active, is_superuser, is_teacher) "
            f"VALUES ({sql_str(username)}, {sql_str(teacher_password)}, {sql_str(email)}, {sql_str(full_name)}, 1, 0, 1);"
        )
    add("")

    # 学生
    add("-- 学生（18 人）")
    for index, full_name in enumerate(STUDENT_NAMES, start=1):
        username = f"pku_cs2401_{index:02d}"
        email = f"{username}@stu.pku.edu.cn"
        add(
            "INSERT IGNORE INTO users (username, password, email, full_name, is_active, is_superuser, is_teacher) "
            f"VALUES ({sql_str(username)}, {sql_str(student_password)}, {sql_str(email)}, {sql_str(full_name)}, 1, 0, 0);"
        )
    add("")

    # 实验室
    add("-- 实验室（8 个）")
    for name, location, capacity, description in LABS:
        add(
            "INSERT IGNORE INTO labs (name, location, capacity, description, status) "
            f"VALUES ({sql_str(name)}, {sql_str(location)}, {capacity}, {sql_str(description)}, 1);"
        )
    add("")

    # 设备
    add("-- 设备（每室 3 台）")
    equipment_code = 0
    for lab_name, *_ in LABS:
        for item in rng.sample(EQUIPMENT, 3):
            equipment_code += 1
            name, kind, description = item
            code = f"PKU-CS-{equipment_code:03d}"
            add(
                "INSERT IGNORE INTO equipment (lab_id, name, code, quantity, description, status) "
                f"SELECT id, {sql_str(name + '（' + lab_name.replace('实验室', '') + '）')}, {sql_str(code)}, "
                f"{rng.randint(1, 6)}, {sql_str(description)}, 1 FROM labs WHERE name = {sql_str(lab_name)};"
            )
    add("")

    # 课程 + 选课
    add("-- 实验课程与选课名单")
    today = date.today()
    semester_end = today + timedelta(days=120)
    for course in COURSES:
        add(
            "INSERT INTO courses (name, lab_id, teacher_id, weekday, start_time, end_time, start_date, end_date, description) "
            f"SELECT {sql_str(course['name'])}, l.id, u.id, {course['weekday']}, "
            f"{sql_str(course['start'])}, {sql_str(course['end'])}, {sql_str(today.isoformat())}, "
            f"{sql_str(semester_end.isoformat())}, "
            f"{sql_str('2026 秋季学期实验课程示例')} "
            f"FROM labs l, users u WHERE l.name = {sql_str(course['lab'])} AND u.username = {sql_str(course['teacher'])} "
            f"AND NOT EXISTS (SELECT 1 FROM courses c WHERE c.name = {sql_str(course['name'])}"
            f" AND c.lab_id = l.id);"
        )
    add("")
    for course in COURSES:
        add(
            "INSERT IGNORE INTO course_enrollments (course_id, student_id) "
            f"SELECT c.id, u.id FROM courses c, users u WHERE c.name = {sql_str(course['name'])} "
            f"AND u.username IN ({', '.join(sql_str(f'pku_cs2401_{i:02d}') for i in range(1, 7))});"
        )
    add("")

    # 预约：未来 12 天，每天每个实验室 1~2 个时段，学生每周 ≤3 条
    add("-- 预约（幂等：同用户/实验室/日期/开始时间已存在则跳过）")
    students = [f"pku_cs2401_{index:02d}" for index in range(1, len(STUDENT_NAMES) + 1)]
    quota: dict[tuple[str, str], int] = {}
    created = 0
    target = 100
    for day_offset in range(1, 13):
        target_date = today + timedelta(days=day_offset)
        iso = target_date.isocalendar()
        week_key = f"{iso[0]}-{iso[1]}"
        for lab_name, *_ in LABS:
            for slot in rng.sample(RESERVATION_SLOTS, 2):
                if created >= target:
                    continue
                candidates = [s for s in students if quota.get((s, week_key), 0) < 3]
                if not candidates:
                    continue
                student = rng.choice(candidates)
                status = "approved" if rng.random() < 0.6 else "pending"
                purpose = rng.choice(PURPOSES) + "（PKU 示例数据）"
                quota[(student, week_key)] = quota.get((student, week_key), 0) + 1
                created += 1
                start, end = slot
                add(
                    "INSERT INTO reservations (user_id, lab_id, reservation_date, start_time, end_time, purpose, status, review_comment) "
                    f"SELECT u.id, l.id, {sql_str(target_date.isoformat())}, {sql_str(start)}, {sql_str(end)}, "
                    f"{sql_str(purpose)}, {sql_str(status)}, "
                    f"{sql_str('示例数据批量导入') if status == 'approved' else 'NULL'} "
                    f"FROM users u, labs l WHERE u.username = {sql_str(student)} AND l.name = {sql_str(lab_name)} "
                    f"AND NOT EXISTS (SELECT 1 FROM reservations r WHERE r.user_id = u.id AND r.lab_id = l.id "
                    f"AND r.reservation_date = {sql_str(target_date.isoformat())} AND r.start_time = {sql_str(start)});"
                )
    add("")
    add(f"-- 共生成预约 {created} 条（学生每周最多 3 条，已按配额控制）")
    add("")
    add("-- ============ 清理示例数据（需要重来时在 Navicat 执行下面语句） ============")
    add("-- DELETE FROM reservations WHERE purpose LIKE '%PKU 示例数据%';")
    add(
        "-- DELETE FROM course_enrollments WHERE course_id IN (SELECT id FROM (SELECT id FROM courses WHERE description = '2026 秋季学期实验课程示例') t);"
    )
    add("-- DELETE FROM courses WHERE description = '2026 秋季学期实验课程示例';")
    add("-- DELETE FROM equipment WHERE code LIKE 'PKU-CS-%';")
    for name, *_ in LABS:
        add(f"-- DELETE FROM labs WHERE name = {sql_str(name)};")
    add(
        "-- DELETE FROM users WHERE username LIKE 'pku_cs2401_%' OR username IN ('pku_teacher_li', 'pku_teacher_wang');"
    )
    add("")
    return "\n".join(lines)


def execute_sql(sql: str) -> int:
    """直接写入当前数据库；返回执行的语句数。"""
    from app.database import engine
    from sqlalchemy import text

    statements = [part.strip() for part in sql.split(";\n") if part.strip()]
    executed = 0
    with engine.begin() as connection:
        for chunk in statements:
            # 只去掉整行注释（不能因为 chunk 以注释开头就整块丢弃——
            # 区块标题后紧跟的第一条 INSERT 会被误删）
            body = "\n".join(line for line in chunk.splitlines() if not line.strip().startswith("--")).strip()
            if not body:
                continue
            connection.execute(text(body))
            executed += 1
    return executed


def main() -> None:
    parser = argparse.ArgumentParser(description="生成并导入北京大学计算机系示例数据")
    parser.add_argument("--out", default=str(OUTPUT))
    parser.add_argument("--execute", action="store_true", help="生成后直接写入当前数据库（backend/.env）")
    args = parser.parse_args()

    sql = build_sql()
    out_path = Path(args.out)
    out_path.write_text(sql, encoding="utf-8")
    print(f"SQL 文件已生成：{out_path}")

    if args.execute:
        try:
            count = execute_sql(sql)
            print(f"已写入数据库，执行 {count} 条语句。")
        except Exception as exc:  # noqa: BLE001
            print(f"数据库写入失败（SQL 文件仍可用 Navicat 运行）：{exc}")


if __name__ == "__main__":
    main()
