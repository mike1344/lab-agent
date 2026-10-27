"""批量生成演示数据：实验室 + 设备 + 预约（可自动审核通过）。

为什么走 HTTP 接口而不是直接 INSERT：这样会真实经过鉴权、参数校验、
预约冲突/配额/课表校验、操作日志与通知逻辑——才叫"检验程序"。

用法（先启动后端；建议批量期间临时关闭限流，见文末提示）：

    # 10 个实验室，每个 2 台设备，3 个学生，造 60 条预约并全部审核通过
    .\\.venv\\Scripts\\python.exe scripts/batch_seed_demo.py --labs 10 --equip 2 --students 3 --reservations 60 --approve

    # 只造实验室/设备
    .\\.venv\\Scripts\\python.exe scripts/batch_seed_demo.py --labs 20 --reservations 0

脚本已处理的业务约束：
- 预约只约未来（明天起，避免"开始时间已过"）；
- 每个用户每个 ISO 周最多 3 条有效预约（与后端配额一致）；
- 同实验室同一天使用互不重叠的时间槽（避免自造冲突）；
- 审核通过前会复核实验室状态（脚本只造 status=1 的实验室）。

限流提示：认证接口 10 次/分钟。若 students > 3，注册+登录会触发 429，
建议批量期间在 backend/.env 临时设置 RATE_LIMIT_ENABLED=false 并重启后端。
"""

import argparse
import random
import time
from datetime import date, timedelta

import httpx

# 互不重叠的时间槽，分散在上午/下午
SLOTS = [
    ("08:00:00", "09:00:00"),
    ("09:30:00", "10:30:00"),
    ("11:00:00", "12:00:00"),
    ("14:00:00", "15:00:00"),
    ("15:30:00", "16:30:00"),
    ("17:00:00", "18:00:00"),
]


def call(client: httpx.Client, method: str, path: str, token: str | None = None, **kwargs) -> dict:
    """调用接口并解包统一响应；失败时抛出带原因的异常。"""
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.request(method, path, headers=headers, **kwargs)
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        payload = {}
    code = payload.get("code", 200)
    if response.status_code >= 400 or code != 200:
        raise RuntimeError(
            f"{method} {path} -> HTTP {response.status_code}, {payload.get('message') or payload.get('detail')}"
        )
    return payload.get("data")


def login(client: httpx.Client, username: str, password: str) -> str:
    data = call(client, "POST", "/api/auth/login", json={"username": username, "password": password})
    return data["token"]


def main() -> None:
    parser = argparse.ArgumentParser(description="批量生成实验室/设备/预约演示数据")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin", default="admin")
    parser.add_argument("--admin-password", default="Admin123456")
    parser.add_argument("--labs", type=int, default=5, help="创建实验室数量")
    parser.add_argument("--equip", type=int, default=2, help="每个实验室创建设备数量")
    parser.add_argument("--students", type=int, default=3, help="创建学生账号数量（认证限流 10/分钟）")
    parser.add_argument("--reservations", type=int, default=30, help="尝试创建的预约数量")
    parser.add_argument("--approve", action="store_true", help="创建后立即审核通过")
    parser.add_argument("--delay", type=float, default=0.2, help="每次写请求间隔秒数，避免触发限流")
    parser.add_argument("--verbose", action="store_true", help="打印每次跳过的原因")
    args = parser.parse_args()

    suffix = str(int(time.time()))[-6:]
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        try:
            admin_token = login(client, args.admin, args.admin_password)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"管理员登录失败（先确认后端已启动、账号密码正确）：{exc}")

        # 1) 实验室 + 设备
        labs = []
        for i in range(args.labs):
            lab = call(
                client,
                "POST",
                "/api/labs",
                admin_token,
                json={
                    "name": f"自测实验室{suffix}-{i + 1:02d}",
                    "location": f"自动化楼 {i // 10 + 1}0{i % 10 + 1}",
                    "capacity": random.randint(6, 40),
                    "status": 1,
                },
            )
            labs.append(lab)
            for j in range(args.equip):
                try:
                    call(
                        client,
                        "POST",
                        "/api/equipment",
                        admin_token,
                        json={
                            "lab_id": lab["id"],
                            "name": f"自测设备{suffix}-{i + 1:02d}-{j + 1}",
                            "code": f"BATCH{suffix}-{i + 1:02d}-{j + 1}",
                            "quantity": random.randint(1, 5),
                        },
                    )
                except RuntimeError as exc:
                    print("设备跳过：", exc)
                time.sleep(args.delay)
            time.sleep(args.delay)
        print(f"[1/3] 实验室 {len(labs)} 个，设备约 {len(labs) * args.equip} 台")

        # 2) 学生账号（注册 + 登录各占 1 次认证限流配额）
        students: list[tuple[str, str]] = []
        for i in range(args.students):
            username = f"batch_stu{suffix}_{i + 1}"
            password = "BatchStu123456"
            try:
                call(
                    client,
                    "POST",
                    "/api/auth/register",
                    json={"username": username, "password": password, "email": f"{username}@example.com"},
                )
            except RuntimeError as exc:
                print("注册跳过：", exc)
            try:
                students.append((login(client, username, password), username))
            except RuntimeError as exc:
                print("登录跳过：", exc)
            time.sleep(args.delay)
        if not students:
            raise SystemExit("没有可用的学生账号，无法创建预约")
        print(f"[2/3] 学生 {len(students)} 个")

        # 3) 预约（含配额与冲突规避）
        created = approved = skipped = 0
        quota: dict[tuple[str, str], int] = {}
        used_slots: set[tuple[int, str, tuple[str, str]]] = set()
        for _ in range(args.reservations * 5):
            if created >= args.reservations:
                break
            token, username = random.choice(students)
            lab = random.choice(labs)
            target = date.today() + timedelta(days=random.randint(1, 20))
            iso = target.isocalendar()
            week_key = f"{iso[0]}-{iso[1]}"
            if quota.get((username, week_key), 0) >= 3:
                continue
            slot = random.choice(SLOTS)
            key = (lab["id"], target.isoformat(), slot)
            if key in used_slots:
                continue
            try:
                data = call(
                    client,
                    "POST",
                    "/api/reservations",
                    token,
                    json={
                        "lab_id": lab["id"],
                        "reservation_date": target.isoformat(),
                        "start_time": slot[0],
                        "end_time": slot[1],
                        "purpose": f"批量自测 {suffix}",
                    },
                )
            except RuntimeError as exc:
                skipped += 1
                if args.verbose:
                    print("预约跳过：", exc)
                time.sleep(args.delay)
                continue
            created += 1
            used_slots.add(key)
            quota[(username, week_key)] = quota.get((username, week_key), 0) + 1
            time.sleep(args.delay)

            for reservation in data:
                if not args.approve:
                    continue
                try:
                    call(
                        client,
                        "PUT",
                        f"/api/reservations/{reservation['id']}/review",
                        admin_token,
                        json={"status": "approved", "review_comment": "批量自测"},
                    )
                    approved += 1
                except RuntimeError as exc:
                    print("审核跳过：", exc)
                time.sleep(args.delay)

        print(f"[3/3] 预约创建 {created} 条，审核通过 {approved} 条，因冲突/配额跳过 {skipped} 次")
        print("完成。到前端 首页统计 / 预约列表 / 报表中心 页查看效果。")


if __name__ == "__main__":
    main()
