from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str
    # 图形验证码凭据：仅当后端开启 LOGIN_CAPTCHA_ENABLED 时必填
    captcha_id: str = ""
    captcha_code: str = ""


class CaptchaResponse(BaseModel):
    # false 表示后端关闭了验证码，前端隐藏输入框
    enabled: bool
    captcha_id: str = ""
    image: str = ""


class LoginResponse(BaseModel):
    token: str
    # 长效刷新令牌：前端在 access token 过期后用它换新 token（无感刷新）
    refresh_token: str = ""
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginLogResponse(BaseModel):
    # from_attributes：允许直接从 SQLAlchemy ORM 对象构造（model_validate）
    model_config = ConfigDict(from_attributes=True)

    username: str
    user_id: int | None = None
    ip: str | None = None
    user_agent: str | None = None
    success: bool
    message: str
    create_time: datetime
