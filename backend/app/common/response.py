from enum import IntEnum
from typing import Any

from pydantic import BaseModel


class BizCode(IntEnum):
    """前后端约定的业务状态码。"""

    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500


class Response(BaseModel):
    """统一封装的返回格式"""

    code: int
    message: str
    data: Any = None

    @classmethod
    def success(cls, message: str = "请求成功", data: Any = None):
        return cls(code=BizCode.SUCCESS, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "请求失败"):
        return cls(code=code, message=message)

