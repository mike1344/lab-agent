"""定时任务：过期预约自动关闭 + 预约开始前站内提醒。

设计要点：
1. 核心逻辑写成“显式接收 db 会话”的纯函数，单元测试可以直接调用，不必真等定时器；
2. APScheduler 的 Job 只负责“开一个新 Session → 调纯函数 → 异常兜底记日志”，
   任务内部绝不复用请求级的 Session；
3. 提醒去重不加表字段：以 notifications 表里是否已存在
   type='reservation_reminder' 且 related_id=预约ID 的记录作为幂等标记，
   重复执行同一任务不会发出重复通知。
"""

import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.notification import Notification
from app.models.reservation import Reservation
from app.services import email as email_service
from app.services.audit import purge_expired_audit_logs
from app.services.ws import push_notification

logger = logging.getLogger("lab_agent.schedule")

# 任务执行间隔（秒）：两个任务都用 5 分钟一次，粒度足够且数据库压力可忽略。
JOB_INTERVAL_SECONDS = 300
# 开课前多少分钟内发提醒。
REMIND_LEAD_MINUTES = 60


def _format_span(reservation: Reservation) -> str:
    return f"{reservation.reservation_date} {reservation.start_time.strftime('%H:%M')}-{reservation.end_time.strftime('%H:%M')}"


def expire_stale_reservations(db: Session) -> int:
    """把“已结束但仍 pending/approved”的预约置为 expired，并通知预约人。

    判定“已结束”的两种情况：
    - 预约日期在今天之前（跨天，含整段已过去的日子）；
    - 预约日期就是今天、但结束时间不晚于当前时刻。
    """
    now = datetime.now()
    stale_filter = or_(
        Reservation.reservation_date < now.date(),
        and_(
            Reservation.reservation_date == now.date(),
            Reservation.end_time <= now.time(),
        ),
    )
    stale = db.query(Reservation).filter(Reservation.status.in_(["pending", "approved"]), stale_filter).all()
    pushed: list[tuple[int, str, str, int]] = []
    for reservation in stale:
        was_pending = reservation.status == "pending"
        reservation.status = "expired"
        title = "预约已自动关闭"
        content = (
            f"您 {_format_span(reservation)} 预约的「{reservation.lab.name}」"
            f"{'已超过审核时限，' if was_pending else '使用时间已结束，'}"
            "记录已由系统自动关闭。"
        )
        db.add(
            Notification(
                user_id=reservation.user_id,
                type="reservation_result",
                title=title,
                content=content,
                related_id=reservation.id,
            )
        )
        pushed.append((reservation.user_id, title, content, reservation.id))
    if stale:
        db.commit()
        for user_id, title, content, related_id in pushed:
            push_notification(
                user_id=user_id, type="reservation_result", title=title, content=content, related_id=related_id
            )
    return len(stale)


def remind_upcoming_reservations(db: Session) -> int:
    """给未来 60 分钟内开始的已通过预约发提醒；已提醒过的不重复发。"""
    now = datetime.now()
    lead_end = now + timedelta(minutes=REMIND_LEAD_MINUTES)

    # 候选集取“今天 + 明天”的已通过预约，用 datetime 精确比较，
    # 避免 23:30~00:00 提醒窗口跨天时 time 比较失真。
    candidates = (
        db.query(Reservation)
        .filter(
            Reservation.status == "approved",
            Reservation.reservation_date.in_([now.date(), now.date() + timedelta(days=1)]),
        )
        .all()
    )
    sent = 0
    pushed: list[tuple[int, str, str, int]] = []
    for reservation in candidates:
        starts_at = datetime.combine(reservation.reservation_date, reservation.start_time)
        if not (now <= starts_at <= lead_end):
            continue
        already_reminded = (
            db.query(Notification.id)
            .filter(
                Notification.user_id == reservation.user_id,
                Notification.type == "reservation_reminder",
                Notification.related_id == reservation.id,
            )
            .first()
        )
        if already_reminded:
            continue
        title = "预约即将开始"
        content = (
            f"您预约的「{reservation.lab.name}」将于 {starts_at.strftime('%H:%M')} 开始，请提前前往并遵守实验室规范。"
        )
        db.add(
            Notification(
                user_id=reservation.user_id,
                type="reservation_reminder",
                title=title,
                content=content,
                related_id=reservation.id,
            )
        )
        pushed.append((reservation.user_id, title, content, reservation.id, reservation.user.email))
        sent += 1
    if sent:
        db.commit()
        for user_id, title, content, related_id, to_email in pushed:
            push_notification(
                user_id=user_id, type="reservation_reminder", title=title, content=content, related_id=related_id
            )
            # 定时任务跑在调度线程里，邮件发送是同步的（10 秒超时），失败也只记日志。
            email_service.send_notification_email(to_email, title, content)
    return sent


def _run_in_fresh_session(job_name: str, job_func) -> None:
    """定时器入口：每个周期一个全新 Session，异常只记日志不中断调度线程。"""
    try:
        with SessionLocal() as db:
            affected = job_func(db)
        if affected:
            logger.info("定时任务 %s 处理了 %s 条记录", job_name, affected)
    except Exception:  # noqa: BLE001 - 调度线程内必须兜底，否则异常会悄悄杀死任务
        logger.exception("定时任务 %s 执行失败", job_name)


def start_scheduler() -> BackgroundScheduler:
    """创建并启动调度器；调用方负责在应用关闭时执行 scheduler.shutdown()。"""
    workers = (os.environ.get("WEB_CONCURRENCY") or "1").strip()
    if workers.isdigit() and int(workers) > 1:
        # 每个 uvicorn worker 都是独立进程，各自跑一份调度器会重复发通知；
        # 提醒任务有幂等去重兜底，过期关闭没有，多进程部署应关闭调度器或只跑单进程。
        logger.warning(
            "WEB_CONCURRENCY=%s：检测到多进程部署，调度任务可能重复执行；"
            "建议设置 SCHEDULER_ENABLED=false 并由单个专用进程承担定时任务。",
            workers,
        )
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        lambda: _run_in_fresh_session("expire_stale_reservations", expire_stale_reservations),
        "interval",
        seconds=JOB_INTERVAL_SECONDS,
        id="expire_stale_reservations",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        lambda: _run_in_fresh_session("remind_upcoming_reservations", remind_upcoming_reservations),
        "interval",
        seconds=JOB_INTERVAL_SECONDS,
        id="remind_upcoming_reservations",
        max_instances=1,
        coalesce=True,
    )
    # 审计日志留存清理：每天 03:00 执行，删除保留期（默认 180 天）之外的登录/操作日志
    scheduler.add_job(
        lambda: _run_in_fresh_session("purge_expired_audit_logs", purge_expired_audit_logs),
        "cron",
        hour=3,
        minute=0,
        id="purge_expired_audit_logs",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
