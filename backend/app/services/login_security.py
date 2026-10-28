"""登录安全组件：图形验证码 + 失败锁定。

两者均为内存实现（线程安全），单机部署开箱即用：
- 进程重启即清零，代价可接受（攻击者绕不过验证码本身）；
- 多 worker（uvicorn WEB_CONCURRENCY>1）部署时各进程独立计数，锁定阈值按进程各算各的，
  需要全局精确控制时可将存储层平滑替换为 Redis（接口不变）。
"""

import base64
import hmac
import io
import secrets
import threading
from datetime import datetime, timedelta

from captcha.image import ImageCaptcha

from app.config import settings

# ==================== 图形验证码 ====================

# 去掉易混淆字符（I、O、0、1），降低用户输入失败率
CAPTCHA_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# captcha_id -> (验证码明文, 过期时间)。验证后立即删除：一次性使用，防重放。
_CAPTCHAS: dict[str, tuple[str, datetime]] = {}
_captcha_lock = threading.Lock()


def create_captcha() -> tuple[str, str]:
    """生成一张 4 位验证码图片，返回 (captcha_id, data URL)。"""
    code = "".join(secrets.choice(CAPTCHA_CHARS) for _ in range(4))
    buffer = io.BytesIO()
    # ImageCaptcha 内置字体，无需额外字体文件；PNG 输出交给前端 <img> 直接展示
    ImageCaptcha(width=140, height=44).write(code, buffer)
    image_data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

    captcha_id = secrets.token_urlsafe(16)
    expire_at = datetime.now() + timedelta(minutes=settings.CAPTCHA_EXPIRE_MINUTES)
    with _captcha_lock:
        _purge_expired_captchas()
        _CAPTCHAS[captcha_id] = (code, expire_at)
    return captcha_id, image_data_url


def verify_captcha(captcha_id: str, code: str) -> bool:
    """校验并消费验证码：无论对错都立即失效。比较用常量时间函数，防时序侧信道。"""
    if not captcha_id or not code:
        return False
    with _captcha_lock:
        _purge_expired_captchas()
        entry = _CAPTCHAS.pop(captcha_id, None)
    if entry is None:
        return False
    stored_code, expire_at = entry
    if datetime.now() > expire_at:
        return False
    return hmac.compare_digest(stored_code.upper(), code.strip().upper())


def _purge_expired_captchas() -> None:
    """惰性清理过期项（调用方需持有 _captcha_lock）。"""
    now = datetime.now()
    expired = [key for key, (_, expire_at) in _CAPTCHAS.items() if expire_at <= now]
    for key in expired:
        _CAPTCHAS.pop(key, None)


# ==================== 失败锁定 ====================

# username -> [失败时间, ...]：滑动窗口统计，窗口外的失败自动失效。
_FAILURES: dict[str, list[datetime]] = {}
_failure_lock = threading.Lock()


def is_locked(username: str) -> bool:
    """窗口内失败次数达到阈值即视为锁定（即使密码正确也拒绝）。"""
    with _failure_lock:
        return len(_failures_in_window(username)) >= settings.LOGIN_MAX_FAILURES


def record_failure(username: str) -> None:
    """记录一次登录失败，并清理窗口外的历史记录。"""
    now = datetime.now()
    with _failure_lock:
        _FAILURES.setdefault(username, []).append(now)
        _FAILURES[username] = _failures_in_window(username, now=now)


def clear_failures(username: str) -> None:
    """登录成功后清空该用户的失败计数。"""
    with _failure_lock:
        _FAILURES.pop(username, None)


def _failures_in_window(username: str, *, now: datetime | None = None) -> list[datetime]:
    """取锁定时间窗口内的失败记录（调用方需持有 _failure_lock）。"""
    now = now or datetime.now()
    window_start = now - timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
    return [t for t in _FAILURES.get(username, []) if t > window_start]
