from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.dependencies.signature import require_signature
from app.models.user import User
from app.schemas.user import (
    AdminUserCreate,
    AdminUserUpdate,
    UserAdminPasswordReset,
    UserPasswordUpdate,
    UserProfileUpdate,
    UserResponse,
)
from app.services.export import build_excel_response
from app.utils.password import hash_password, verify_password

router = APIRouter(prefix="/user", tags=["用户信息接口"])


@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息，前端刷新页面后可用它恢复登录状态。"""
    return Response.success(data=UserResponse.model_validate(current_user))


@router.put("/profile")
def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户修改自己的姓名、邮箱与头像。"""
    email = str(data.email).lower()
    email_owner = db.query(User).filter(User.email == email, User.id != current_user.id).first()
    if email_owner:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="邮箱已被其他账号使用")

    current_user.email = email
    current_user.full_name = data.full_name.strip() if data.full_name else None
    # avatar_url 只在请求里显式携带时更新，避免“保存资料”把已有头像清空。
    if "avatar_url" in data.model_fields_set:
        current_user.avatar_url = data.avatar_url
    db.commit()
    db.refresh(current_user)
    return Response.success(
        message="个人信息修改成功",
        data=UserResponse.model_validate(current_user),
    )


@router.put("/password")
def update_password(
    data: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码前再次校验旧密码，避免登录会话被盗后直接改密。"""
    if not verify_password(data.old_password, current_user.password):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="原密码不正确")
    if data.old_password == data.new_password:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="新密码不能与原密码相同")

    current_user.password = hash_password(data.new_password)
    db.commit()
    return Response.success(message="密码修改成功，请重新登录")


@router.get("")
def get_user_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员分页查询用户；用户名、姓名和邮箱都支持模糊搜索。"""
    query = db.query(User)
    if keyword.strip():
        search_value = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                User.username.like(search_value),
                User.full_name.like(search_value),
                User.email.like(search_value),
            )
        )

    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Response.success(
        data={
            "list": [UserResponse.model_validate(user) for user in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/export")
def export_users(
    keyword: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员导出用户列表（与用户管理筛选一致）。"""
    query = db.query(User)
    if keyword.strip():
        search_value = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                User.username.like(search_value),
                User.full_name.like(search_value),
                User.email.like(search_value),
            )
        )
    users = query.order_by(User.id.asc()).all()
    rows = [
        [
            user.id,
            user.username,
            user.full_name or "",
            user.email,
            "管理员" if user.is_superuser else ("教师" if user.is_teacher else "学生"),
            "启用" if user.is_active else "禁用",
            str(user.create_time),
        ]
        for user in users
    ]
    return build_excel_response(
        sheet_title="用户列表",
        headers=["ID", "用户名", "姓名", "邮箱", "角色", "状态", "创建时间"],
        rows=rows,
        filename_prefix="用户列表",
    )


@router.post("")
def create_user(
    data: AdminUserCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员新增普通用户或管理员账号。"""
    username = data.username.strip()
    email = str(data.email).lower()
    if db.query(User).filter(or_(User.username == username, User.email == email)).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="用户名或邮箱已存在")

    user = User(
        username=username,
        password=hash_password(data.password),
        email=email,
        full_name=data.full_name.strip() if data.full_name else None,
        is_active=data.is_active,
        is_superuser=data.is_superuser,
        is_teacher=data.is_teacher,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return Response.success(message="用户新增成功", data=UserResponse.model_validate(user))


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员修改账号资料、角色和启用状态。"""
    user = db.get(User, user_id)
    if not user:
        raise BusinessException(code=BizCode.NOT_FOUND, message="用户不存在")
    if user.id == current_admin.id and data.is_active is False:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="不能禁用当前登录账号")
    if user.id == current_admin.id and data.is_superuser is False:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="不能取消自己的管理员权限")

    update_data = data.model_dump(exclude_unset=True)
    if "email" in update_data:
        update_data["email"] = str(update_data["email"]).lower()
        exists = db.query(User).filter(User.email == update_data["email"], User.id != user_id).first()
        if exists:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="邮箱已被其他账号使用")
    if update_data.get("full_name"):
        update_data["full_name"] = update_data["full_name"].strip()

    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return Response.success(message="用户修改成功", data=UserResponse.model_validate(user))


@router.put("/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    data: UserAdminPasswordReset,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员重置任意用户密码，不需要知道原密码。"""
    user = db.get(User, user_id)
    if not user:
        raise BusinessException(code=BizCode.NOT_FOUND, message="用户不存在")
    user.password = hash_password(data.new_password)
    db.commit()
    return Response.success(message="密码已重置")


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    _sig: User = Depends(require_signature),
    db: Session = Depends(get_db),
):
    """删除用户。已产生预约记录的用户应优先禁用，数据库会阻止误删。"""
    if user_id == current_admin.id:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="不能删除当前登录账号")
    user = db.get(User, user_id)
    if not user:
        raise BusinessException(code=BizCode.NOT_FOUND, message="用户不存在")

    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="该用户已有业务数据，请改为禁用账号",
        )
    return Response.success(message="用户删除成功")
