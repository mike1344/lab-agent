"""操作日志审计中间件：统一记录所有写操作。

设计取舍：
- 与应用逻辑解耦：不侵入各业务接口，靠 ASGI 中间件统一拦截写请求；
- 只记录 POST/PUT/PATCH/DELETE，读操作不产生噪音；
- 登录/注册已由 login_logs 覆盖，AI 流式对话与 WebSocket 不在此记录；
- 审计是旁路：写日志失败只打告警，绝不影响接口本身的结果。
"""

import inspect
import json
import logging
import time

from fastapi import Request
from starlette.responses import Response

from app.database import SessionLocal
from app.models.operation_log import OperationLog
from app.models.user import User
from app.utils.jwt import decode_access_token

logger = logging.getLogger("lab_agent")

# 只有这些方法会产生操作日志
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# 排除前缀：登录/注册已有 login_logs；AI 对话是流式响应；上传的静态文件不是业务写操作。
EXCLUDED_PREFIXES = ("/api/auth/", "/api/ai/", "/api/ws/", "/uploads/")


def _client_ip(request: Request) -> str:
    """取客户端 IP：nginx 反代时 X-Forwarded-For 的第一段才是真实来源。"""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "")[:64]


def _route_summary(request: Request) -> str:
    """操作说明：优先取路由文档字符串首行（中文字段，便于审计阅读），没有则用函数名。"""
    route = request.scope.get("route")
    endpoint = getattr(route, "endpoint", None)
    if endpoint is not None:
        doc = inspect.getdoc(endpoint) or ""
        if doc:
            return doc.splitlines()[0].strip().rstrip("。")[:100]
    return str(getattr(route, "name", "") or "")[:100]


def _resolve_operator(request: Request) -> tuple[str, int | None, bool]:
    """从 Authorization 头解析操作人；解析失败按未登录记录（非法凭证也要留痕）。"""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return "(未登录)", None, False
    token = auth_header[7:].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        return "(无效凭证)", None, False
    user_id = payload.get("user_id")
    if not user_id:
        return "(无效凭证)", None, False

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            return "(未知用户)", user_id, False
        return user.username, user.id, bool(user.is_superuser)
    except Exception:  # noqa: BLE001 - 解析失败按占位符记录
        return "(未知用户)", user_id, False
    finally:
        db.close()


def _write_log(
    request: Request,
    *,
    summary: str,
    success: bool,
    http_status: int,
    message: str,
    duration_ms: float,
) -> None:
    """独立会话写入一条操作日志；任何异常只告警不抛出。"""
    username, user_id, is_superuser = _resolve_operator(request)
    db = SessionLocal()
    try:
        db.add(
            OperationLog(
                username=username,
                user_id=user_id,
                is_superuser=is_superuser,
                method=request.method,
                path=request.url.path[:255],
                summary=summary[:100],
                success=success,
                http_status=int(http_status),
                message=message[:255],
                ip=_client_ip(request),
                duration_ms=int(duration_ms),
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001 - 审计失败不影响接口
        db.rollback()
        logger.warning("操作日志写入失败 | 路径:%s", request.url.path)
    finally:
        db.close()


async def operation_log_middleware(request: Request, call_next):
    """写请求结束后落一条审计日志；读请求直接放行。"""
    if request.method not in WRITE_METHODS or request.url.path.startswith(EXCLUDED_PREFIXES):
        return await call_next(request)

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # 未捕获异常会继续向上抛给全局处理器，这里先把失败事实记录下来。
        _write_log(
            request,
            summary=_route_summary(request),
            success=False,
            http_status=500,
            message="服务器未捕获异常",
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        raise

    # 读取 JSON 响应体，从统一信封里取业务码与提示；流式/文件响应不做缓冲，只看 HTTP 状态码。
    content_type = response.headers.get("content-type", "")
    envelope: dict = {}
    if content_type.startswith("application/json"):
        body = b"".join([chunk async for chunk in response.body_iterator])
        response = Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            background=response.background,
        )
        try:
            envelope = json.loads(body) if body else {}
        except Exception:  # noqa: BLE001 - 非 JSON 响应按 HTTP 状态判断
            envelope = {}

    code = envelope.get("code")
    success = code == 200 if isinstance(code, int) else response.status_code < 400
    _write_log(
        request,
        summary=_route_summary(request),
        success=success,
        http_status=response.status_code,
        message=str(envelope.get("message") or ""),
        duration_ms=(time.perf_counter() - started) * 1000,
    )
    return response
