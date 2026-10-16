from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=64)
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        """注册和管理员新增用户共用这条规则，防止全空格用户名入库。"""
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("用户名至少需要 3 个非空白字符")
        return cleaned


class AdminUserCreate(UserCreate):
    is_active: bool = True
    is_superuser: bool = False
    is_teacher: bool = False


class UserProfileUpdate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=64)


class UserAdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=64)


class AdminUserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_teacher: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        # 管理员编辑时，None 只适用于可选的姓名；邮箱、角色和状态必须有值。
        required_fields = ("email", "is_active", "is_superuser", "is_teacher")
        if any(field in self.model_fields_set and getattr(self, field) is None for field in required_fields):
            raise ValueError("用户必填字段不能设为 null")
        return self


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    is_teacher: bool
    avatar_url: str | None = None
    create_time: datetime

    model_config = ConfigDict(from_attributes=True)
