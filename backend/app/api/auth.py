from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserCreate, UserResponse
from app.utils.jwt import create_access_token
from app.utils.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["权限验证"])


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # 根据用户账号查询数据库
    user = db.query(User).filter(User.username == data.username).first()

    # 判断账号和密码是否正确
    if not user or not verify_password(data.password, user.password):
        # 登录凭证错误属于 401，而不是服务器内部错误。
        raise BusinessException(code=BizCode.UNAUTHORIZED, message="账号或密码错误")
    # 验证账号的状态
    if not user.is_active:
        # 凭证本身正确，但账号状态不允许继续访问，因此返回 403。
        raise BusinessException(code=BizCode.FORBIDDEN, message="账号被禁用")
    # 创建token
    token = create_access_token(user.id, user.password)
    # 返回信息
    return Response.success(
        message="登录成功",
        data=LoginResponse(token=token, user=UserResponse.model_validate(user)),
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
