import hashlib
import secrets
from datetime import datetime, timedelta

import jwt

from app.config import settings


def build_password_version(password_hash: str) -> str:
    """生成密码版本指纹，用于让改密前签发的 Token 自动失效。

    JWT 只保存哈希的 SHA-256 指纹，不暴露数据库里的 bcrypt 密码哈希。
    用户修改密码后 bcrypt 哈希发生变化，鉴权时指纹不再匹配旧 Token。
    """
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def create_access_token(user_id: int, password_hash: str) -> str:
    """创建短效访问令牌（type=access），附带密码版本用于改密后强制失效。"""
    expire = datetime.now() + timedelta(hours=settings.JWT_EXPIRE_HOURS)

    payload = {
        "user_id": user_id,
        "password_version": build_password_version(password_hash),
        "type": "access",
        "jti": secrets.token_hex(8),  # 唯一标识：同一秒内多次签发也不会得到相同字符串
        "exp": expire,  # exp 是 JWT 标准字段，PyJWT 会自动校验。
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int, password_hash: str) -> str:
    """创建长效刷新令牌（type=refresh），由 /api/auth/refresh 换取新的访问令牌。

    不落库：吊销依赖密码版本指纹——改密后旧 refresh token 立即失效，
    代价是无法单独踢掉某台设备的会话（多会话精细吊销需要 refresh token 表）。
    """
    expire = datetime.now() + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    payload = {
        "user_id": user_id,
        "password_version": build_password_version(password_hash),
        "type": "refresh",
        "jti": secrets.token_hex(8),
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析jwt token"""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
