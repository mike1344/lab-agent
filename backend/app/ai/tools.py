from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.blackout import BlackoutPeriod
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.common.exceptions import BusinessException
from app.schemas.reservation import ReservationCreate
from app.services.reservation import create_reservation_record


TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "list_open_labs", "description": "查询当前开放的实验室以及可用设备", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "search_lab_docs", "description": "查询实验室预约规则、设备使用规范等知识库文档", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "create_lab_reservation", "description": "信息完整并得到用户明确要求后，创建实验室预约", "parameters": {"type": "object", "properties": {"lab_id": {"type": "integer"}, "reservation_date": {"type": "string", "description": "YYYY-MM-DD"}, "start_time": {"type": "string", "description": "HH:MM"}, "end_time": {"type": "string", "description": "HH:MM"}, "purpose": {"type": "string"}}, "required": ["lab_id", "reservation_date", "start_time", "end_time", "purpose"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "get_my_reservations", "description": "查询当前用户的预约记录，可按状态筛选", "parameters": {"type": "object", "properties": {"status": {"type": "string", "enum": ["pending", "approved", "rejected", "cancelled"], "description": "预约状态，留空查全部"}}, "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "cancel_reservation", "description": "取消用户自己的预约，需要提供预约ID", "parameters": {"type": "object", "properties": {"reservation_id": {"type": "integer", "description": "要取消的预约ID"}}, "required": ["reservation_id"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "check_lab_availability", "description": "查询某实验室某天哪些时段已被占用或不可约", "parameters": {"type": "object", "properties": {"lab_id": {"type": "integer"}, "reservation_date": {"type": "string", "description": "YYYY-MM-DD"}}, "required": ["lab_id", "reservation_date"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "get_latest_announcements", "description": "查询系统最新公告", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "recommend_lab", "description": "根据日期、时间段偏好和需要时长，智能推荐有空位的实验室。学生说想什么时候做实验但没指定实验室时用这个工具", "parameters": {"type": "object", "properties": {"reservation_date": {"type": "string", "description": "YYYY-MM-DD"}, "period": {"type": "string", "enum": ["morning", "afternoon", "evening"], "description": "偏好时段：上午=8-12点，下午=13-18点，晚上=18-22点"}, "duration_hours": {"type": "integer", "description": "需要几小时，默认2"}}, "required": ["reservation_date", "period"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "get_today", "description": "获取今天的日期和星期几。用户说今天、明天、后天时先用这个换算成具体日期", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "list_lab_equipments", "description": "查询所有实验室的设备列表，包括设备名、数量和所属实验室", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, "strict": True},
]


def list_open_labs(db: Session) -> str:
    labs = db.query(Lab).filter(Lab.status == 1).order_by(Lab.id).all()
    if not labs:
        return "当前没有开放的实验室。"
    lines = []
    for lab in labs:
        equipment = db.query(Equipment).filter(Equipment.lab_id == lab.id, Equipment.status == 1, Equipment.quantity > 0).all()
        equipment_text = "、".join(f"{item.name}×{item.quantity}" for item in equipment) or "暂无登记设备"
        lines.append(f"实验室ID {lab.id}：{lab.name}，位置 {lab.location}，容量 {lab.capacity} 人；设备：{equipment_text}")
    return "\n".join(lines)


def create_lab_reservation(db: Session, user_id: int, arguments: dict) -> str:
    try:
        lab_id = int(arguments["lab_id"])
        reservation_date = date.fromisoformat(arguments["reservation_date"])
        start_time = time.fromisoformat(arguments["start_time"])
        end_time = time.fromisoformat(arguments["end_time"])
        # 用途没给就默认填"AI智能预约"，不强制用户提供
        purpose = str(arguments.get("purpose") or "AI智能预约").strip() or "AI智能预约"
    except (KeyError, TypeError, ValueError):
        return "预约信息格式不完整，请提供实验室、日期、开始时间、结束时间。"

    # 自动获取用户姓名，不用问用户
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    user_label = user.full_name or user.username if user else f"用户#{user_id}"

    try:
        data = ReservationCreate(
            lab_id=lab_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
        )
        created, skipped = create_reservation_record(db, user_id, data)
    except (BusinessException, ValueError) as exc:
        return getattr(exc, "message", str(exc))
    result = f"✅ 预约成功！申请人：{user_label}，{len(created)}条预约编号 {', '.join(str(r.id) for r in created)}，状态为待审核。"
    if skipped:
        result += f"跳过：{'；'.join(skipped)}"
    return result


def get_my_reservations(db: Session, user_id: int, status: str | None = None) -> str:
    query = db.query(Reservation).filter(Reservation.user_id == user_id)
    if status:
        query = query.filter(Reservation.status == status)
    items = query.order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc()).limit(20).all()
    if not items:
        return "你当前没有预约记录。"
    status_map = {"pending": "待审核", "approved": "已通过", "rejected": "已拒绝", "cancelled": "已取消"}
    lines = [f"预约共 {len(items)} 条："]
    for r in items:
        lab_name = r.lab.name if r.lab else "未知"
        lines.append(f"#{r.id} {lab_name} {r.reservation_date} {r.start_time.strftime('%H:%M')}-{r.end_time.strftime('%H:%M')} [{status_map.get(r.status, r.status)}] 用途：{r.purpose}")
    return "\n".join(lines)


def cancel_reservation(db: Session, user_id: int, reservation_id: int) -> str:
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        return f"预约 #{reservation_id} 不存在。"
    if reservation.user_id != user_id:
        return f"预约 #{reservation_id} 不是你的，无法取消。"
    if reservation.status not in ("pending", "approved"):
        return f"预约 #{reservation_id} 当前状态为{reservation.status}，不能取消。"
    reservation.status = "cancelled"
    db.commit()
    return f"预约 #{reservation_id} 已取消。"


def check_lab_availability(db: Session, lab_id: int, reservation_date: str) -> str:
    try:
        d = date.fromisoformat(reservation_date)
    except ValueError:
        return "日期格式错误，请用 YYYY-MM-DD。"
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        return f"实验室 #{lab_id} 不存在。"
    items = db.query(Reservation).filter(
        Reservation.lab_id == lab_id,
        Reservation.reservation_date == d,
        Reservation.status.in_(["pending", "approved"]),
    ).order_by(Reservation.start_time).all()
    blackouts = db.query(BlackoutPeriod).filter(
        BlackoutPeriod.lab_id == lab_id,
        BlackoutPeriod.blackout_date == d,
    ).order_by(BlackoutPeriod.start_time).all()
    if not items and not blackouts:
        return f"{lab.name} {reservation_date} 全天空闲，没有已占用或不可约时段。"
    lines = [f"{lab.name} {reservation_date} 不可用时段："]
    for r in items:
        st = "已通过" if r.status == "approved" else "待审核"
        lines.append(f"  {r.start_time.strftime('%H:%M')}-{r.end_time.strftime('%H:%M')}（{r.user.full_name if r.user else '?'}，{st}）")
    for b in blackouts:
        lines.append(f"  {b.start_time.strftime('%H:%M')}-{b.end_time.strftime('%H:%M')}（不可约：{b.reason}）")
    return "\n".join(lines)


def get_latest_announcements(db: Session, limit: int = 5) -> str:
    items = db.query(Announcement).order_by(Announcement.id.desc()).limit(limit).all()
    if not items:
        return "当前没有系统公告。"
    lines = ["最新公告："]
    for a in items:
        lines.append(f"【{a.title}】{a.content[:100]}")
    return "\n".join(lines)


def recommend_lab(db: Session, reservation_date: str, period: str, duration_hours: int = 2) -> str:
    """根据时间段偏好智能推荐有空位的实验室，返回详细选项。

    占用来源既包括已有预约，也包括管理员设置的不可约时段；当天只推荐
    当前时间之后的时段，避免推荐结果在创建时被“开始时间已过”拦住。
    """
    try:
        d = date.fromisoformat(reservation_date)
    except ValueError:
        return "日期格式错误，请用 YYYY-MM-DD。"

    period_map = {
        "morning": (time(8, 0), time(12, 0)),
        "afternoon": (time(13, 0), time(18, 0)),
        "evening": (time(18, 0), time(22, 0)),
    }
    range_start, range_end = period_map.get(period, period_map["afternoon"])
    need_minutes = duration_hours * 60

    now = datetime.now()
    if d < now.date():
        return f"{reservation_date} 已经过去，请选择今天或之后的日期。"
    if d == now.date():
        # 今天把起点抬到下一个 30 分钟刻度，跳过已经过去的时段。
        current_minutes = now.hour * 60 + now.minute
        rounded_minutes = (current_minutes // 30 + 1) * 30
        range_end_minutes = range_end.hour * 60 + range_end.minute
        if rounded_minutes >= range_end_minutes:
            return f"今天 {period} 时段已经过去，建议换个时段或改到明天。"
        range_start = time(hour=rounded_minutes // 60, minute=rounded_minutes % 60)

    labs = db.query(Lab).filter(Lab.status == 1).order_by(Lab.id).all()
    if not labs:
        return "当前没有开放的实验室。"

    results = []
    for lab in labs:
        occupied = db.query(Reservation).filter(
            Reservation.lab_id == lab.id,
            Reservation.reservation_date == d,
            Reservation.status.in_(["pending", "approved"]),
        ).all()
        blackouts = db.query(BlackoutPeriod).filter(
            BlackoutPeriod.lab_id == lab.id,
            BlackoutPeriod.blackout_date == d,
        ).all()

        # 预约与不可约时段合并成统一占用列表，再找该时段内最长的空闲段。
        blocked = sorted(
            [(r.start_time, r.end_time) for r in occupied]
            + [(b.start_time, b.end_time) for b in blackouts]
        )
        free_starts = range_start
        best_free = None
        for block_start, block_end in blocked:
            if block_end <= range_start or block_start >= range_end:
                continue
            gap_start = max(free_starts, range_start)
            gap_end = min(block_start, range_end)
            gap_min = (datetime.combine(d, gap_end) - datetime.combine(d, gap_start)).total_seconds() / 60
            if gap_min >= need_minutes:
                if not best_free or gap_min > best_free[2]:
                    best_free = (gap_start, gap_end, gap_min)
            free_starts = max(free_starts, block_end)
        gap_start = max(free_starts, range_start)
        gap_end = range_end
        gap_min = (datetime.combine(d, gap_end) - datetime.combine(d, gap_start)).total_seconds() / 60
        if gap_min >= need_minutes:
            if not best_free or gap_min > best_free[2]:
                best_free = (gap_start, gap_end, gap_min)

        if best_free:
            # 查这个实验室的设备
            equipments = db.query(Equipment).filter(
                Equipment.lab_id == lab.id, Equipment.status == 1, Equipment.quantity > 0
            ).all()
            equip_text = "、".join(f"{e.name}×{e.quantity}" for e in equipments) or "无"
            start_dt = datetime.combine(d, best_free[0])
            end_dt = start_dt + timedelta(hours=duration_hours)
            results.append(
                f"实验室ID {lab.id}：{lab.name}（{lab.location}，容量{lab.capacity}人）\n"
                f"  可约时段：{best_free[0].strftime('%H:%M')}-{end_dt.strftime('%H:%M')}\n"
                f"  设备：{equip_text}"
            )

    if not results:
        return f"{reservation_date} 在该时段没有实验室能腾出 {duration_hours} 小时连续空位，建议换个时间段。"
    return f"以下实验室在 {reservation_date} {period} 有空位（已为你选好{duration_hours}小时时段）：\n\n" + "\n\n".join(results)


def get_today() -> str:
    """返回今天日期和星期，方便 AI 换算明天/后天。"""
    today = date.today()
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    lines = [f"今天是 {today.isoformat()}（{weekday_names[today.weekday()]}）。"]
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    lines.append(f"明天是 {tomorrow.isoformat()}（{weekday_names[tomorrow.weekday()]}）。")
    lines.append(f"后天是 {day_after.isoformat()}（{weekday_names[day_after.weekday()]}）。")
    return "\n".join(lines)


def list_lab_equipments(db: Session) -> str:
    """查询所有设备。"""
    items = db.query(Equipment).filter(Equipment.status == 1, Equipment.quantity > 0).order_by(Equipment.lab_id, Equipment.id).all()
    if not items:
        return "当前没有登记可用设备。"
    lines = []
    current_lab = None
    for eq in items:
        lab_name = eq.lab.name if eq.lab else f"实验室#{eq.lab_id}"
        if lab_name != current_lab:
            lines.append(f"【{lab_name}】")
            current_lab = lab_name
        lines.append(f"  {eq.name}：{eq.quantity} 台，位置：{eq.location or '-'}")
    return "\n".join(lines)
