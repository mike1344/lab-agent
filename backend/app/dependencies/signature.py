"""危险操作二次确认（电子签名），带验证有效期。

语义：
- 每次危险操作（删除实验室/设备/用户/公告、驳回预约）都要求输入当前账号密码；
- 密码验证通过后 **在 SIGNATURE_TTL_MINUTES（默认 5 分钟）内**重复危险操作
  不需要再次输入（类似 sudo 的免密窗口），超时后重新要求输入；
- TTL 设为 0 时退化为「每次都必须输入」；
- 缓存按用户 + 当前密码指纹保存：改密后旧缓存自动失效；进程重启即清空；
- 多 worker 部署时各进程独立缓存（与限流/验证码同样的取舍）。

与操作日志配合构成「电子签名」证据链：谁（JWT 身份）、何时（日志时间）、
做了什么（接口路径）、结果（成功/失败）都有据可查。
"""

import hashlib
import threading
import time

from fastapi import Depends, Query

from app.common.exceptions import BusinessException
from app.common.response import BizCode
from app.config import settings
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.utils.password import verify_password

# user_id -> (到期时间 monotonic 秒, 密码指纹)
_verified: dict[int, tuple[float, str]] = {}
_verified_lock = threading.Lock()


def _fingerprint(password_hash: str) -> str:
    """密码指纹：改密后旧缓存自动失效。"""
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def reset_signature_cache() -> None:
    """测试或运维手动清空二次验证缓存。"""
    with _verified_lock:
        _verified.clear()


def _signature_still_valid(current_user: User) -> bool:
    """TTL 内且密码未变 → 视为已通过二次确认。"""
    if settings.SIGNATURE_TTL_MINUTES <= 0:
        return False
    with _verified_lock:
        entry = _verified.get(current_user.id)
        if not entry:
            return False
        expires_at, fingerprint = entry
        if expires_at <= time.monotonic() or fingerprint != _fingerprint(current_user.password):
            _verified.pop(current_user.id, None)
            return False
        return True


def _remember_signature(current_user: User) -> None:
    ttl_seconds = settings.SIGNATURE_TTL_MINUTES * 60
    if ttl_seconds <= 0:
        return
    with _verified_lock:
        _verified[current_user.id] = (
            time.monotonic() + ttl_seconds,
            _fingerprint(current_user.password),
        )


def verify_signature(password: str, current_user: User) -> None:
    """校验二次确认密码；不通过直接抛业务异常。"""
    if not settings.SIGNATURE_REQUIRED:
        return
    if _signature_still_valid(current_user):
        return
    if not password:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message=(f"危险操作需要输入当前账号密码二次确认（验证有效期 {settings.SIGNATURE_TTL_MINUTES} 分钟）"),
        )
    if not verify_password(password, current_user.password):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="密码不正确，操作已取消")
    _remember_signature(current_user)


async def require_signature(
    signature_password: str = Query(default=""),
    current_user: User = Depends(get_current_user),
) -> User:
    """作为依赖挂到危险接口上：先校验密码再执行；返回当前用户供端点使用。"""
    verify_signature(signature_password, current_user)
    return current_user
