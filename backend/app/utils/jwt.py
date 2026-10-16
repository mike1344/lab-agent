import hashlib
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
    """创建带过期时间和密码版本的 JWT Token。"""
    expire = datetime.now() + timedelta(hours=settings.JWT_EXPIRE_HOURS)

    payload = {
        "user_id": user_id,
        "password_version": build_password_version(password_hash),
        "exp": expire,  # exp 是 JWT 标准字段，PyJWT 会自动校验。
    }

    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

def decode_access_token(token: str) -> dict:
    """解析jwt token"""
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
