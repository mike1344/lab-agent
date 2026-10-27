"""请求上下文：把 request_id 绑定到 ContextVar，日志与业务代码都能读到。

- 日志格式化器通过 RequestIdFilter 把当前请求 ID 注入每条日志；
- 业务代码（如审计中间件的告警日志）也可以直接调用 get_request_id()；
- 使用 ContextVar 而不是全局变量，多个并发请求互不串号。
"""

from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str):
    """设置当前请求 ID，返回 reset token 供 finally 中还原。"""
    return _request_id.set(value)
