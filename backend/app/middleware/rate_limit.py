"""接口限流：内存固定窗口计数（按 IP + 规则分组）。

规则（.env 可调）：
- 认证类（登录/注册/刷新）默认 10 次/分钟；
- AI 接口默认 30 次/分钟；
- 其余 /api 接口默认 120 次/分钟。

内存实现：进程重启清零、多 worker 各自计数（阈值实际被放大）；
需要集群级精确限流时把存储换 Redis 即可，判定逻辑不变。
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings

WINDOW_SECONDS = 60
_lock = threading.Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)

# 不参与限流的路径：探活、指标、静态资源与接口文档
_SKIP_PREFIXES = ("/health", "/ready", "/metrics", "/uploads", "/docs", "/openapi", "/redoc")


def _rule_for(path: str) -> tuple[str, int] | None:
    """返回 (规则名, 每分钟上限)；无需限流时返回 None。"""
    if path.startswith(_SKIP_PREFIXES):
        return None
    if path.startswith(("/api/auth/login", "/api/auth/register", "/api/auth/refresh")):
        return "auth", settings.RATE_LIMIT_AUTH_PER_MINUTE
    if path.startswith("/api/ai/"):
        return "ai", settings.RATE_LIMIT_AI_PER_MINUTE
    if path.startswith("/api/"):
        return "api", settings.RATE_LIMIT_PER_MINUTE
    return None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def reset_rate_limits() -> None:
    """测试或运维手动清空计数。"""
    with _lock:
        _buckets.clear()


async def rate_limit_middleware(request: Request, call_next):
    if not settings.RATE_LIMIT_ENABLED:
        return await call_next(request)

    rule = _rule_for(request.url.path)
    if rule is None:
        return await call_next(request)

    name, limit = rule
    key = f"{name}:{_client_ip(request)}"
    now = time.monotonic()
    with _lock:
        bucket = _buckets[key]
        while bucket and now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"code": 429, "message": "请求过于频繁，请稍后再试", "data": None},
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
        bucket.append(now)
    return await call_next(request)
