"""请求 ID 中间件 + 结构化日志配置。

链路追踪的最小可用方案：
1. 入口生成（或沿用上游传入的）X-Request-ID，写入 ContextVar；
2. 日志格式化器统一输出 [request_id]，同一次请求的多条日志可以串起来；
3. 响应头回写 X-Request-ID，前端/网关报错时可直接带上这个 ID 查日志。
"""

import logging
import uuid

from fastapi import Request

from app.common import context as request_context
from app.common.context import set_request_id

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdFilter(logging.Filter):
    """给每条日志补上当前请求的 request_id。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_context.get_request_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    """统一日志格式；重复调用只更新级别，避免叠加 handler 导致日志翻倍。"""
    root = logging.getLogger()
    if getattr(root, "_lab_agent_configured", False):
        root.setLevel(level)
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(level)
    root._lab_agent_configured = True  # type: ignore[attr-defined]


async def request_id_middleware(request: Request, call_next):
    """为每个请求生成/透传 X-Request-ID，并写回响应头。"""
    incoming = request.headers.get(REQUEST_ID_HEADER, "").strip()
    request_id = incoming[:64] if incoming else uuid.uuid4().hex
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        # 必须还原，否则协程复用/并发时 request_id 会串到下个请求
        request_context._request_id.reset(token)
