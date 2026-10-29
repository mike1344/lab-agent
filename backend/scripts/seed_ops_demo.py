"""批量生成演示数据：设备 + 采购 + 报修 + 预约。

目标：
- 给每个实验室补充设备（数量按实验室容量和现有设备规模做基本配比）；
- 为新增设备生成「申请中 / 已到货 / 已验收」采购记录，验收记录只入库一次；
- 为部分设备生成待处理 / 处理中 / 已解决的报修记录；
- 按每周配额和冲突规则批量生成未来预约。

幂等：设备按 OPS- 编号、采购按备注标记、报修按标题、预约按用途前缀去重；
重复执行不会重复入库或重复插入。只用于本地/演示库。

用法（backend 目录）：
    .\\.venv\\Scripts\\python.exe scripts\\seed_ops_demo.py
"""

import sys
from datetime import date, time, timedelta
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.equipment import Equipment  # noqa: E402
from app.models.lab import Lab  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.procurement import Procurement  # noqa: E402
from app.models.repair import Repair  # noqa: E402
from app.models.reservation import Reservation  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.reservation import check_slot_available  # noqa: E402
from app.utils.password import hash_password  # noqa: E402

EQUIPMENT_CATALOG = [
    "高性能工作站",
    "数字示波器",
    "网络测试仪",
    "嵌入式开发板套件",
    "传感器实验套件",
    "投影与显示设备",
    "精密电源",
    "数据采集卡",
]
CONSUMABLES = ["实验耗材包", "连接线缆套装", "防静电工具包", "存储与备份介质"]
SLOTS = [(time(13, 0), time(14, 0)), (time(14, 30), time(15, 30)), (time(16, 0), time(17, 0))]
PURPOSE_PREFIX = "OPS 批量预约："


def ensure_equipment(db, lab: Lab, index: int, base_quantity: int = 1) -> Equipment | None:
    code = f"OPS-{lab.id:02d}-{index:02d}"
    equipment = db.query(Equipment).filter(Equipment.code == code).first()
    if equipment is not None:
        return equipment
    name = f"{EQUIPMENT_CATALOG[index % len(EQUIPMENT_CATALOG)]}（{lab.name}）"
    equipment = Equipment(
        lab_id=lab.id,
        name=name,
        code=code,
        quantity=base_quantity,
        description="OPS 演示数据：批量配置设备",
        status=1,
    )
    db.add(equipment)
    db.flush()
    return equipment


def ensure_procurement(db, admin: User, equipment: Equipment, status: str, quantity: int) -> bool:
    marker = f"OPS-SEED:{equipment.id}:{status}:{quantity}"
    if db.query(Procurement).filter(Procurement.remark == marker).first():
        return False
    name = f"OPS 采购：{equipment.name}"
    item = Procurement(
        equipment_id=equipment.id,
        name=name,
        quantity=quantity,
        applicant_id=admin.id,
        status=status,
        remark=marker,
    )
    db.add(item)
    if status == "accepted":
        # 直接种子数据也遵守“验收才入库、且只入库一次”
        equipment.quantity += quantity
    db.flush()
    return True


def ensure_repair(db, admin: User, lab: Lab, equipment: Equipment | None, index: int) -> bool:
    if equipment is not None:
        title = f"OPS 报修：{equipment.name}"
    else:
        title = f"OPS 报修：{lab.name} 环境问题"
    if db.query(Repair).filter(Repair.title == title).first():
        return False

    statuses = ["pending", "processing", "resolved"]
    status = statuses[index % len(statuses)]
    reporter = db.query(User).filter(User.is_superuser.is_(False), User.is_active.is_(True)).order_by(User.id).first()
    if reporter is None:
        return False

    handler_id = admin.id if status in ("processing", "resolved") else None
    handle_comment = {
        "pending": None,
        "processing": "已联系厂商，等待备件到货",
        "resolved": "已更换故障模块并完成复测",
    }[status]
    item = Repair(
        reporter_id=reporter.id,
        lab_id=lab.id,
        equipment_id=equipment.id if equipment is not None else None,
        title=title,
        description=f"OPS 演示数据：{lab.name}{'设备' if equipment else '实验室环境'}异常，请安排处理。",
        status=status,
        handler_id=handler_id,
        handle_comment=handle_comment,
    )
    db.add(item)
    db.flush()
    if status != "pending":
        db.add(
            Notification(
                user_id=reporter.id,
                type="repair_result",
                title=f"报修进度更新：{'处理中' if status == 'processing' else '已解决'}",
                content=f"你提交的报修「{title}」状态已更新。处理备注：{handle_comment or '无'}",
                related_id=item.id,
            )
        )
    return True


def ensure_ops_students(db, count: int = 8) -> list[User]:
    """创建专用演示学生，避免和已有预约的每周配额冲突。"""
    students: list[User] = []
    for index in range(1, count + 1):
        username = f"ops_student_{index:02d}"
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            user = User(
                username=username,
                password=hash_password("Student123456"),
                email=f"{username}@example.com",
                full_name=f"OPS 学生 {index:02d}",
                is_active=True,
                is_superuser=False,
                is_teacher=False,
            )
            db.add(user)
            db.flush()
        students.append(user)
    return students


def seed_reservations(db, labs: list[Lab], students: list[User], target: int = 40) -> int:
    # 幂等：已有 OPS 预约计入目标，避免重复执行时再补一批
    existing_total = db.query(Reservation).filter(Reservation.purpose.like(f"{PURPOSE_PREFIX}%")).count()
    created = 0
    today = date.today()
    for offset in range(1, 8):
        target_date = today + timedelta(days=offset)
        for lab in labs:
            for slot_index, (start, end) in enumerate(SLOTS):
                if existing_total + created >= target:
                    return created
                student = students[(created + slot_index) % len(students)]
                purpose = f"{PURPOSE_PREFIX}{lab.name} {target_date} {start.strftime('%H:%M')}"
                exists = (
                    db.query(Reservation)
                    .filter(
                        Reservation.user_id == student.id,
                        Reservation.lab_id == lab.id,
                        Reservation.reservation_date == target_date,
                        Reservation.start_time == start,
                        Reservation.purpose.like(f"{PURPOSE_PREFIX}%"),
                    )
                    .first()
                )
                if exists:
                    continue
                reason = check_slot_available(db, student.id, lab.id, target_date, start, end)
                if reason:
                    continue
                status = "approved" if created % 10 < 6 else "pending"
                db.add(
                    Reservation(
                        user_id=student.id,
                        lab_id=lab.id,
                        reservation_date=target_date,
                        start_time=start,
                        end_time=end,
                        purpose=purpose,
                        status=status,
                        review_comment="OPS 批量预约示例" if status == "approved" else None,
                    )
                )
                db.flush()
                created += 1
    return created


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.is_superuser.is_(True), User.is_active.is_(True)).order_by(User.id).first()
        if admin is None:
            raise SystemExit("没有可用的管理员账号，请先运行 scripts/create_admin.py")
        students = ensure_ops_students(db)
        if not students:
            raise SystemExit("没有可用的学生账号，请先导入演示数据")

        labs = db.query(Lab).filter(Lab.status == 1).order_by(Lab.id).all()
        # E2E 实验室留给端到端脚本，避免污染固定断言
        labs = [lab for lab in labs if not lab.name.startswith("E2E")]

        equipment_created = 0
        procurement_created = 0
        repair_created = 0

        for lab in labs:
            # 按容量配 2 种新增设备；容量越大，单种数量越高
            per_type = max(1, min(3, lab.capacity // 10))
            new_items: list[Equipment] = []
            for index in range(2):
                before = db.query(Equipment).filter(Equipment.code == f"OPS-{lab.id:02d}-{index:02d}").first()
                equipment = ensure_equipment(db, lab, index, base_quantity=1)
                if equipment is None:
                    continue
                new_items.append(equipment)
                if before is None:
                    equipment_created += 1
                # 验收数量 = 目标数量 - 初始 1；另外各留一条到货/申请中记录
                if per_type > 1:
                    procurement_created += int(ensure_procurement(db, admin, equipment, "accepted", per_type - 1))
                procurement_created += int(ensure_procurement(db, admin, equipment, "arrived", 1))
                procurement_created += int(ensure_procurement(db, admin, equipment, "pending", 1))

            # 每个实验室一条耗材采购
            consumable_name = f"OPS 采购：{CONSUMABLES[lab.id % len(CONSUMABLES)]}（{lab.name}）"
            if not db.query(Procurement).filter(Procurement.name == consumable_name).first():
                db.add(
                    Procurement(
                        equipment_id=None,
                        name=consumable_name,
                        quantity=5,
                        applicant_id=admin.id,
                        status="pending",
                        remark=f"OPS-SEED:consumable:{lab.id}",
                    )
                )
                procurement_created += 1
                db.flush()

            # 每个实验室挑一台新设备报修
            if new_items:
                repair_created += int(ensure_repair(db, admin, lab, new_items[0], lab.id))

        # 额外生成少量实验室环境报修
        for lab in labs[:4]:
            repair_created += int(ensure_repair(db, admin, lab, None, lab.id + 1))

        reservation_created = seed_reservations(db, labs, students, target=40)
        db.commit()

        print("OPS 演示数据生成完成")
        print(f"  新增设备：{equipment_created}")
        print(f"  新增采购：{procurement_created}")
        print(f"  新增报修：{repair_created}")
        print(f"  新增预约：{reservation_created}")
        print(f"  使用管理员：{admin.username}")
        print("  演示学生账号：ops_student_01 .. ops_student_08 / Student123456")

        print("\n当前统计：")
        for table in ["equipment", "procurements", "repairs", "reservations"]:
            count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
