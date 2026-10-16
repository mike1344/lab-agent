"""初始化参考清华大学计算机系教学中心设置的演示实验室。

实验室名称参考清华大学计算机国家级实验教学中心公开页面：
https://lab.cs.tsinghua.edu.cn/

注意：公开页面没有提供本预约系统所需的房间位置、可预约人数等字段，
因此 ``location`` 和 ``capacity`` 使用课程项目演示值，不代表清华大学
真实场地、容量或开放预约情况。
"""

from app.database import Base, SessionLocal, engine
from app.models import Equipment, Lab, Reservation, User  # noqa: F401


# 名称来自官方公开页面；其余字段是为了演示预约系统而补充的模拟数据。
LABS = [
    {
        "name": "计算机硬件技术基础实验室",
        "location": "计算机系教学实验区（演示）",
        "capacity": 40,
        "description": "面向计算机硬件技术基础实验教学。位置和容量为课程项目演示值。",
        "status": 1,
    },
    {
        "name": "单片机技术实验室",
        "location": "计算机系教学实验区（演示）",
        "capacity": 32,
        "description": "面向单片机原理、控制与实践教学。位置和容量为课程项目演示值。",
        "status": 1,
    },
    {
        "name": "计算机网络应用实验室",
        "location": "计算机系教学实验区（演示）",
        "capacity": 48,
        "description": "面向全校的计算机网络应用实验教学。位置和容量为课程项目演示值。",
        "status": 1,
    },
    {
        "name": "计算机系统软件实验室",
        "location": "计算机系专业实验区（演示）",
        "capacity": 40,
        "description": "面向操作系统、编译与系统软件相关实验教学。位置和容量为课程项目演示值。",
        "status": 1,
    },
    {
        "name": "计算机组成原理实验室",
        "location": "计算机系专业实验区（演示）",
        "capacity": 32,
        "description": "面向计算机组成原理与体系结构基础实验。位置和容量为课程项目演示值。",
        "status": 1,
    },
    {
        "name": "微机与接口技术实验室",
        "location": "计算机系专业实验区（演示）",
        "capacity": 32,
        "description": "面向微型计算机、接口技术与外设控制实验。位置和容量为课程项目演示值。",
        "status": 1,
    },
    {
        "name": "嵌入式技术与系统实验室",
        "location": "计算机系专业实验区（演示）",
        "capacity": 30,
        "description": "面向嵌入式软硬件与系统开发实验。位置和容量为课程项目演示值。",
        "status": 1,
    },
    {
        "name": "计算机网络原理实验室",
        "location": "计算机系专业实验区（演示）",
        "capacity": 40,
        "description": "面向计算机网络协议、组网与网络原理实验。位置和容量为课程项目演示值。",
        "status": 1,
    },
    {
        "name": "计算机科技创新实验室",
        "location": "计算机系创新实践区（演示）",
        "capacity": 24,
        "description": "面向学生科技创新、综合实践与竞赛项目。位置和容量为课程项目演示值。",
        "status": 1,
    },
]


def main() -> None:
    """只新增数据库中尚不存在的实验室，保证脚本可安全重复执行。"""
    Base.metadata.create_all(bind=engine)

    created_names: list[str] = []
    skipped_names: list[str] = []

    with SessionLocal() as db:
        # 一次取出已有名称，避免循环中为每条数据单独查询数据库。
        existing_names = {name for (name,) in db.query(Lab.name).all()}

        for lab_data in LABS:
            if lab_data["name"] in existing_names:
                skipped_names.append(lab_data["name"])
                continue

            db.add(Lab(**lab_data))
            created_names.append(lab_data["name"])

        # 所有记录作为同一个事务提交：要么一起成功，要么一起失败。
        db.commit()

    print(f"新增实验室：{len(created_names)} 个")
    for name in created_names:
        print(f"  + {name}")

    print(f"跳过同名实验室：{len(skipped_names)} 个")
    for name in skipped_names:
        print(f"  = {name}")


if __name__ == "__main__":
    main()
