import hmac
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.config import settings
from app.database import get_db
from app.dependencies.permission import get_current_admin
from app.models.login_log import LoginLog
from app.models.user import User
from app.schemas.auth import (
    CaptchaResponse,
    LoginLogResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
)
from app.schemas.user import UserCreate, UserResponse
from app.services import login_security
from app.services.export import build_excel_response
from app.utils.jwt import (
    build_password_version,
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from app.utils.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["权限验证"])


def _client_ip(request: Request) -> str:
    """取客户端 IP：nginx 反代时 X-Forwarded-For 的第一段才是真实来源。"""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "")[:64]


def _write_login_log(
    db: Session,
    *,
    request: Request,
    username: str,
    success: bool,
    message: str,
    user_id: int | None = None,
) -> None:
    """每次登录尝试都落一条日志；审计写失败不能反过来阻断登录主流程。"""
    try:
        db.add(
            LoginLog(
                username=username[:50],
                user_id=user_id,
                ip=_client_ip(request),
                user_agent=(request.headers.get("user-agent") or "")[:255],
                success=success,
                message=message[:100],
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001 - 审计日志失败仅回滚，不影响登录结果
        db.rollback()


@router.get("/captcha")
def get_captcha():
    """获取图形验证码。enabled=false 表示后端关闭了验证码，前端据此隐藏输入框。"""
    if not settings.LOGIN_CAPTCHA_ENABLED:
        return Response.success(data=CaptchaResponse(enabled=False))
    captcha_id, image = login_security.create_captcha()
    return Response.success(data=CaptchaResponse(enabled=True, captcha_id=captcha_id, image=image))


@router.post("/login")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    username = data.username.strip()

    # 1. 失败锁定：窗口内连续失败达到阈值后，即使密码正确也暂时拒绝
    if login_security.is_locked(username):
        raise BusinessException(
            code=BizCode.FORBIDDEN,
            message=f"登录失败次数过多，账号已锁定，请 {settings.LOGIN_LOCKOUT_MINUTES} 分钟后再试",
        )

    # 2. 图形验证码：一次性消费，且放在密码校验之前，防止绕过验证码爆破密码
    if settings.LOGIN_CAPTCHA_ENABLED and not login_security.verify_captcha(data.captcha_id, data.captcha_code):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="验证码错误或已过期")

    # 根据用户账号查询数据库
    user = db.query(User).filter(User.username == username).first()

    # 判断账号和密码是否正确
    if not user or not verify_password(data.password, user.password):
        # 登录凭证错误属于 401，而不是服务器内部错误。
        login_security.record_failure(username)
        _write_login_log(db, request=request, username=username, success=False, message="账号或密码错误")
        raise BusinessException(code=BizCode.UNAUTHORIZED, message="账号或密码错误")
    # 验证账号的状态
    if not user.is_active:
        # 凭证本身正确，但账号状态不允许继续访问，因此返回 403；不计入失败锁定。
        _write_login_log(db, request=request, username=username, success=False, message="账号被禁用", user_id=user.id)
        raise BusinessException(code=BizCode.FORBIDDEN, message="账号被禁用")

    # 登录成功：清空失败计数，写入成功日志
    login_security.clear_failures(username)
    _write_login_log(db, request=request, username=username, success=True, message="登录成功", user_id=user.id)
    # 创建短效访问令牌 + 长效刷新令牌
    token = create_access_token(user.id, user.password)
    refresh_token = create_refresh_token(user.id, user.password)
    # 返回信息
    return Response.success(
        message="登录成功",
        data=LoginResponse(token=token, refresh_token=refresh_token, user=UserResponse.model_validate(user)),
    )


@router.post("/refresh")
def refresh_access_token(data: RefreshRequest, db: Session = Depends(get_db)):
    """用 refresh token 换新的访问令牌（前端 401 时自动调用，实现无感刷新）。

    校验链：签名/过期 → type=refresh → 用户存在且启用 → 密码版本一致。
    改密后旧 refresh token 与旧 access token 一起失效；返回的新 refresh token 做轮换。
    """
    try:
        payload = decode_access_token(data.refresh_token)
    except Exception:
        raise BusinessException(code=BizCode.UNAUTHORIZED, message="刷新凭证无效或已过期")
    if payload.get("type") != "refresh":
        raise BusinessException(code=BizCode.UNAUTHORIZED, message="刷新凭证无效或已过期")

    user = db.get(User, payload.get("user_id"))
    if not user or not user.is_active:
        raise BusinessException(code=BizCode.UNAUTHORIZED, message="账号不可用，请重新登录")
    if not hmac.compare_digest(payload.get("password_version", ""), build_password_version(user.password)):
        raise BusinessException(code=BizCode.UNAUTHORIZED, message="密码已修改，请重新登录")

    return Response.success(
        message="刷新成功",
        data={
            "token": create_access_token(user.id, user.password),
            "refresh_token": create_refresh_token(user.id, user.password),
        },
    )


@router.get("/login-logs")
def list_login_logs(
    page: int = 1,
    page_size: int = 50,
    username: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """登录审计日志（管理员）：按时间倒序分页，可按用户名精确过滤。"""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    query = db.query(LoginLog)
    if username.strip():
        query = query.filter(LoginLog.username == username.strip())
    total = query.count()
    items = query.order_by(desc(LoginLog.id)).offset((page - 1) * page_size).limit(page_size).all()
    return Response.success(
        data={
            "total": total,
            "items": [LoginLogResponse.model_validate(item) for item in items],
        }
    )


@router.get("/login-logs/export")
def export_login_logs(
    username: str = "",
    start_date: str = "",
    end_date: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员导出登录审计报告（按用户名/时间范围）。"""
    query = db.query(LoginLog)
    if username.strip():
        query = query.filter(LoginLog.username == username.strip())
    if start_date:
        query = query.filter(LoginLog.create_time >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(LoginLog.create_time < datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
    items = query.order_by(LoginLog.id.asc()).all()
    rows = [
        [
            item.id,
            item.username,
            item.user_id or "",
            item.ip or "",
            item.user_agent or "",
            "成功" if item.success else "失败",
            item.message,
            str(item.create_time),
        ]
        for item in items
    ]
    return build_excel_response(
        sheet_title="登录审计",
        headers=["ID", "用户名", "用户ID", "IP", "UA", "结果", "说明", "时间"],
        rows=rows,
        filename_prefix="登录审计",
    )


@router.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    """注册普通用户账号。"""
    username = data.username.strip()
    full_name = data.full_name.strip() if data.full_name else None

    if len(username) < 3:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="用户名至少需要 3 个字符")

    if db.query(User).filter(User.username == username).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="用户名已存在")
    if db.query(User).filter(User.email == data.email).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="邮箱已被注册")

    user = User(
        username=username,
        password=hash_password(data.password),
        email=str(data.email).lower(),
        full_name=full_name,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise BusinessException(code=BizCode.BAD_REQUEST, message="用户名或邮箱已存在")

    return Response.success(
        message="注册成功",
        data=UserResponse.model_validate(user),
    )
