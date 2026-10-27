import logging

from app.common.response import BizCode, Response
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("lab_agent")


class BusinessException(Exception):
    """自定义业务异常"""

    def __init__(self, message: str, code: int = BizCode.INTERNAL_ERROR):
        self.message = message
        self.code = code
        super().__init__(message)


async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器。

    响应体仍保持项目统一的 ``code/message/data`` 结构，同时让 HTTP 状态码
    真实反映错误类型。这样浏览器、ApiPost、反向代理和监控系统都能正确判断
    请求是否成功，而不需要只依赖响应体中的业务码。
    """
    logger.warning(f"业务异常 | 路径:{request.url.path} | 错误:{exc.message}")
    code = int(exc.code)
    http_status = code if 400 <= code <= 599 else int(BizCode.INTERNAL_ERROR)
    return JSONResponse(
        status_code=http_status,
        content=Response.error(code=exc.code, message=exc.message).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP原生异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=Response.error(code=exc.status_code, message=str(exc.detail)).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验异常：把Pydantic的具体错误提取出来给前端"""
    first_err = exc.errors()[0]
    err_field = ".".join([str(i) for i in first_err["loc"]])
    err_msg = first_err["msg"]
    detail = f"参数错误：{err_field} {err_msg}"
    return JSONResponse(
        # 参数没有通过 Pydantic 校验，属于客户端请求错误。
        status_code=int(BizCode.BAD_REQUEST),
        content=Response.error(code=BizCode.BAD_REQUEST, message=detail).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception):
    """全局兜底异常：记录完整错误栈，不把内部细节暴露给前端"""
    logger.exception(f"未捕获异常 | 路径:{request.url.path}")  # 自动打完整traceback
    return JSONResponse(
        # 未知异常使用真实 500，方便日志平台和调用方触发告警或重试。
        status_code=int(BizCode.INTERNAL_ERROR),
        content=Response.error(code=BizCode.INTERNAL_ERROR, message="服务器开小差了，请稍后重试").model_dump(),
    )
