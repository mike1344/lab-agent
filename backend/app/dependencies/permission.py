from fastapi import Depends

from app.common.exceptions import BusinessException
from app.common.response import BizCode
from app.dependencies.auth import get_current_user
from app.models.user import User


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """验证当前用户是否为管理员，供后台管理接口复用。"""
    if not current_user.is_superuser:
        raise BusinessException(code=BizCode.FORBIDDEN, message="当前账号没有管理权限")
    return current_user


def get_current_staff(current_user: User = Depends(get_current_user)) -> User:
    """验证当前用户是否为管理员或教师，供预约审核等教学管理接口复用。"""
    if not current_user.is_superuser and not current_user.is_teacher:
        raise BusinessException(code=BizCode.FORBIDDEN, message="当前账号没有审核权限")
    return current_user
