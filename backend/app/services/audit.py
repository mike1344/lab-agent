"""审计日志留存策略。

《网络安全法》第 21 条要求网络日志留存不少于 6 个月；`AUDIT_RETENTION_DAYS`
默认 180 天，由定时任务每天凌晨清理一次过期记录，避免日志表无限膨胀。
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models.login_log import LoginLog
from app.models.operation_log import OperationLog

logger = logging.getLogger("lab_agent.audit")


def purge_expired_audit_logs(db: Session) -> int:
    """删除早于保留期的登录日志与操作日志，返回删除条数。"""
    cutoff = datetime.now() - timedelta(days=settings.AUDIT_RETENTION_DAYS)
    deleted = db.query(OperationLog).filter(OperationLog.create_time < cutoff).delete(synchronize_session=False)
    deleted += db.query(LoginLog).filter(LoginLog.create_time < cutoff).delete(synchronize_session=False)
    if deleted:
        db.commit()
        logger.info("审计日志清理：删除 %s 条早于 %s 的记录", deleted, cutoff.date())
    return deleted
