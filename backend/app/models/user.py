from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    # 数据库表名，前后都是两个下划线
    __tablename__ = "users"

    # 表注释
    __table_args__ = {"comment": "用户表"}

    # id、create_time、update_time 从 Base 继承，不需要重复定义

    # 用户名：必填、不可重复
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名",
    )

    # 只保存密码哈希，禁止保存用户输入的明文密码
    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希值，非明文密码",
    )

    # 邮箱：必填、不可重复
    email: Mapped[str] = mapped_column(
        String(254),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱",
    )

    # 姓名：允许不填写，因此类型也允许 None
    full_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="姓名",
    )

    # 账号是否启用：默认启用
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="账号是否启用：True启用，False禁用",
    )

    # 是否为超级管理员：默认普通用户
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为超级管理员：True是，False否",
    )

    # 是否为教师：教师可审核预约
    is_teacher: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为教师：True是，False否",
    )

    # 头像URL：上传后保存
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="头像URL",
    )
