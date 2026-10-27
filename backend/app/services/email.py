"""邮件通知：SMTP 发送（未配置时静默跳过，与 AI Key 相同的降级风格）。

设计要点：
- 用标准库 smtplib + EmailMessage，不引入额外依赖；
- 不配置 SMTP_HOST/SMTP_FROM 时 send_notification_email 直接返回 False，
  不尝试连接任何服务器（开发/测试环境零副作用）；
- 发送失败只记 warning 日志，绝不把异常抛给业务主流程；
- 由 FastAPI BackgroundTasks 在响应之后调用（同步函数由框架放进线程池），
  审核、报修等接口不会因为 SMTP 慢而变慢。
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("lab_agent")


def email_configured() -> bool:
    """是否配置了最基本的发信参数（主机 + 发件人）。"""
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def build_notification_email(to_email: str, subject: str, body: str) -> EmailMessage:
    """纯函数：组装通知邮件；与网络无关，便于单元测试。"""
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    return message


def send_notification_email(to_email: str, subject: str, body: str) -> bool:
    """发送通知邮件；返回是否真正发出。未配置或失败都返回 False（不抛异常）。"""
    if not to_email or not email_configured():
        return False
    message = build_notification_email(to_email, subject, body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as client:
            if settings.SMTP_USE_TLS:
                client.starttls()
            if settings.SMTP_USERNAME:
                client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            client.send_message(message)
        return True
    except Exception:  # noqa: BLE001 - 邮件失败不能影响业务
        # 不打印收件人与正文，避免日志里出现个人信息
        logger.warning("邮件发送失败 | 主题:%s", subject)
        return False
