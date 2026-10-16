# 第 09–14 节：用户功能逐课复现（知识点 ↔ 完整代码对照）

> 本份是「**知识点 ↔ 完整代码**」对照版。用户功能前后端共用几个文件（`schemas/user.py`、`api/user.py`、`user.vue`、`api/user.js`），为避免同一文件重复贴五遍：**第 09 节**贴完整 `schemas/user.py`，**第 11 节**贴完整 `api/user.py`，**文末附录**贴完整 `user.vue`，其余各课用「指向附录的定位表 + 关键片段」说明。纯 CSS 省略，代码均按本仓库核对。

## 第 09 节：开发用户注册功能

**知识点清单：** Pydantic `Field`/`EmailStr`/`field_validator` 输入校验、ORM `unique=True` 唯一约束、bcrypt 存哈希不存明文、公开注册固定为普通用户、`IntegrityError` 兜底并发冲突、前端确认密码只校验不上送。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 输入模型与去空白校验 | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `UserCreate`、`strip_username` |
| 用户名/邮箱唯一 | [`backend/app/models/user.py`](../../backend/app/models/user.py) | `unique=True`（第 04 节已贴） |
| 密码哈希 | [`backend/app/utils/password.py`](../../backend/app/utils/password.py) | `hash_password`（第 05 节已贴） |
| 注册接口 | [`backend/app/api/auth.py`](../../backend/app/api/auth.py) | `register()` |
| 注册 API | [`fronted/src/api/auth.js`](../../fronted/src/api/auth.js) | `registerApi` |
| 注册页面 | [`fronted/src/views/register.vue`](../../fronted/src/views/register.vue) | 完整组件（见下） |

**完整源码：**

[`backend/app/schemas/user.py`](../../backend/app/schemas/user.py)（当前完整内容；本文件同时被第 11–14 节复用）：

```python
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


class UserProfileUpdate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=64)


class AdminUserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    is_superuser: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        # 管理员编辑时，None 只适用于可选的姓名；邮箱、角色和状态必须有值。
        required_fields = ("email", "is_active", "is_superuser")
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
    create_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

[`backend/app/api/auth.py`](../../backend/app/api/auth.py) 中的 `register()`（当前完整函数）：

```python
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
```

[`fronted/src/api/auth.js`](../../fronted/src/api/auth.js) 中的 `registerApi`（`loginApi` 已在第 03 节）：

```js
export function registerApi(data) {
  return request.post('/api/auth/register', data)
}
```

[`fronted/src/views/register.vue`](../../fronted/src/views/register.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 省略）：

```vue
<template>
  <div class="register-container">
    <div class="register-box">
      <h2 class="register-title">注册账号</h2>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" :prefix-icon="User" placeholder="3～20 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="registerForm.email" :prefix-icon="Message" placeholder="用于账号识别" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="registerForm.full_name" :prefix-icon="Postcard" placeholder="选填" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            :prefix-icon="Lock"
            type="password"
            placeholder="8～64 个字符"
            autocomplete="new-password"
            show-password
            @change="revalidateConfirmPassword"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            :prefix-icon="Lock"
            type="password"
            placeholder="请再次输入密码"
            autocomplete="new-password"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="loadingValue"
          class="submit-button"
        >
          注册
        </el-button>

        <div class="login-link">
          已有账号？
          <router-link to="/login">返回登录</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock, Message, Postcard } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { registerApi } from '@/api/auth'

const router = useRouter()
const registerFormRef = ref(null)
const loadingValue = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  full_name: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入密码'))
  else if (value !== registerForm.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const rules = {
  username: [
    { required: true, whitespace: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为 3～20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8～64 个字符', trigger: 'blur' }
  ],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }]
}

const revalidateConfirmPassword = () => {
  if (registerForm.confirmPassword) {
    registerFormRef.value?.validateField('confirmPassword').catch(() => {})
  }
}

const handleRegister = async () => {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid || loadingValue.value) return

  loadingValue.value = true
  try {
    await registerApi({
      username: registerForm.username.trim(),
      email: registerForm.email.trim(),
      full_name: registerForm.full_name.trim() || null,
      password: registerForm.password
    })
    ElMessage.success('注册成功，请使用新账号登录')
    await router.replace('/login')
  } finally {
    loadingValue.value = false
  }
}
</script>
```

**数据流：** `confirmPassword` 只参与前端校验，`registerApi` 的对象里没有它；`is_superuser=False` 由服务端写死，即使请求 JSON 里带 `is_superuser: true` 也不会进入 `UserCreate` 的创建语句。

**验证：** 两次密码不一致前端拦截；重复用户名/邮箱报 400；`/docs` 里故意加 `is_superuser: true`，返回的 `data.is_superuser` 仍为 `false`。

## 第 10 节：开发文件上传 API

**知识点清单：** `UploadFile = File(...)` + 登录依赖、`FormData` 传 `multipart/form-data`、有界读取 `MAX_IMAGE_SIZE + 1`、MIME 与文件头双重校验、随机 UUID 文件名、`StaticFiles` 挂载 `/uploads`、`el-upload` 手动上传。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 格式/大小/文件头识别 | [`backend/app/api/upload.py`](../../backend/app/api/upload.py) | `ALLOWED_IMAGE_TYPES`、`MAX_IMAGE_SIZE`、`detect_image_suffix` |
| 上传接口 | 同文件 | `upload_image()` |
| 静态挂载 | [`backend/app/main.py`](../../backend/app/main.py) | `app.mount("/uploads", ...)`（第 04 节已贴） |
| FormData 封装 | [`fronted/src/api/user.js`](../../fronted/src/api/user.js) | `uploadImageApi` |
| 手动上传控件 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `el-upload` + `handleUploadChange`（完整页见文末附录） |

**完整源码：**

[`backend/app/api/upload.py`](../../backend/app/api/upload.py)（当前完整内容）：

```python
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["文件上传"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def detect_image_suffix(content: bytes) -> str | None:
    """根据文件内容识别图片类型，不能只相信客户端声明的 MIME。

    这里检查三种格式最关键的文件头/尾标记，足以拦截把脚本或文本伪装成图片的
    常见情况。正式图片处理服务还可以再用 Pillow 解码并重新编码一次。
    """
    if (
        content.startswith(b"\x89PNG\r\n\x1a\n")
        and content[12:16] == b"IHDR"
        and b"IEND" in content[-24:]
    ):
        return ".png"
    if content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9"):
        return ".jpg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """上传图片并返回静态访问地址，限制类型和 5MB 大小。"""
    declared_suffix = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not declared_suffix:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="只支持 JPG、PNG、WEBP 图片",
        )

    content = await file.read(MAX_IMAGE_SIZE + 1)
    await file.close()
    if len(content) > MAX_IMAGE_SIZE:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="图片大小不能超过 5MB")

    detected_suffix = detect_image_suffix(content)
    if not detected_suffix or detected_suffix != declared_suffix:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="图片内容与文件类型不匹配",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{detected_suffix}"
    (UPLOAD_DIR / filename).write_bytes(content)
    return Response.success(
        message="上传成功",
        data={"filename": filename, "url": f"/uploads/{filename}"},
    )
```

[`fronted/src/api/user.js`](../../fronted/src/api/user.js)（当前完整内容；本文件被第 10–14 节共用）：

```js
import request from '@/utils/request'

export function getUserInfoApi() {
  return request.get('/api/user/info')
}

export function updateProfileApi(data) {
  return request.put('/api/user/profile', data)
}

export function updatePasswordApi(data) {
  return request.put('/api/user/password', data)
}

export function getUserListApi(params) {
  return request.get('/api/user', { params })
}

export function createUserApi(data) {
  return request.post('/api/user', data)
}

export function updateUserApi(userId, data) {
  return request.put(`/api/user/${userId}`, data)
}

export function deleteUserApi(userId) {
  return request.delete(`/api/user/${userId}`)
}

export function uploadImageApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/upload/image', formData)
}
```

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中与上传相关的片段（完整页面见文末附录）：

```vue
<el-upload :auto-upload="false" :show-file-list="false" accept="image/jpeg,image/png,image/webp" :on-change="handleUploadChange">
  <el-button :loading="uploadingValue">选择并上传图片</el-button>
</el-upload>
<img v-if="uploadedImageUrl" :src="uploadedImageUrl" alt="上传预览" />
<span v-else>支持 JPG、PNG、WEBP，最大 5MB</span>
```

```js
const handleUploadChange = async (uploadFile) => {
  if (!uploadFile.raw) return
  uploadingValue.value = true
  try {
    const res = await uploadImageApi(uploadFile.raw)
    uploadedImageUrl.value = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}${res.data.url}`
    ElMessage.success('图片上传成功')
  } finally { uploadingValue.value = false }
}
```

**数据流：** `el-upload` 的 `uploadFile.raw` 是浏览器 `File` → `FormData` 字段名 `file`（与后端参数同名）→ 后端校验后生成 `filename` 和相对 `url` → 前端拼 API 地址预览。刷新页面后预览消失，因为当前**没有** `avatar_url` 字段和保存接口，“上传成功”不等于“头像已持久化”。

**验证：** 上传真实 PNG/JPEG/WEBP 能看到预览；`/docs` 传改名为 `.png` 的文本文件被拒；无 Token 返回 401。

## 第 11 节：修改个人信息与共享用户状态

**知识点清单：** `GET /api/user/info` 读当前用户、`PUT /api/user/profile` 只改姓名邮箱、邮箱占用检查排除自己、`current_user` 由依赖注入而非请求体、响应式共享 `userInfo`。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 读取/修改接口 | [`backend/app/api/user.py`](../../backend/app/api/user.py) | `get_user_info`、`update_profile` |
| 输入模型 | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `UserProfileUpdate`（第 09 节已贴） |
| 共享用户状态 | [`fronted/src/utils/user.js`](../../fronted/src/utils/user.js) | `useUser`（第 03 节已贴完整） |
| 个人资料表单 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `saveProfile`（完整页见附录） |

**完整源码：**

[`backend/app/api/user.py`](../../backend/app/api/user.py)（当前完整内容；本文件同时被第 12–14 节复用）：

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.user import User
from app.schemas.user import (
    AdminUserCreate,
    AdminUserUpdate,
    UserPasswordUpdate,
    UserProfileUpdate,
    UserResponse,
)
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
    """用户修改自己的姓名与邮箱。"""
    email = str(data.email).lower()
    email_owner = db.query(User).filter(User.email == email, User.id != current_user.id).first()
    if email_owner:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="邮箱已被其他账号使用")

    current_user.email = email
    current_user.full_name = data.full_name.strip() if data.full_name else None
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
    users = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Response.success(
        data={
            "list": [UserResponse.model_validate(user) for user in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
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


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
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
```

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中个人资料部分（完整页见附录）：

```vue
<el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="90px" class="narrow-form">
  <el-form-item label="用户名"><el-input :model-value="userInfo?.username" disabled /></el-form-item>
  <el-form-item label="姓名" prop="full_name"><el-input v-model="profileForm.full_name" placeholder="请输入姓名" /></el-form-item>
  <el-form-item label="邮箱" prop="email"><el-input v-model="profileForm.email" placeholder="请输入邮箱" /></el-form-item>
  <el-form-item label="账号角色"><el-tag :type="isAdmin ? 'danger' : 'success'">{{ isAdmin ? '管理员' : '普通用户' }}</el-tag></el-form-item>
  <el-form-item><el-button type="primary" :loading="savingValue" @click="saveProfile">保存个人信息</el-button></el-form-item>
</el-form>
```

```js
const profileForm = reactive({ full_name: '', email: '' })
const profileRules = { email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }] }

const saveProfile = async () => {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const res = await updateProfileApi({ email: profileForm.email.trim(), full_name: profileForm.full_name.trim() || null })
    updateUser(res.data)
    ElMessage.success('个人信息修改成功')
  } finally { savingValue.value = false }
}
```

**数据流：** `request.js` 自动加 Bearer → `get_current_user` 得到当前用户 → 接口不接收 `user_id` → 邮箱检查 `User.id != current_user.id` 避免误报 → `updateUser(res.data)` 同时更新本地缓存和共享状态。

**验证：** 改姓名/邮箱后页面与接口一致、刷新保持；改成他人已占用邮箱得 400；请求体里塞 `user_id` 不会改变修改目标。

## 第 12 节：修改密码与旧 Token 失效

**知识点清单：** 验证旧密码、拒绝新旧相同、存新 bcrypt 哈希、`password_version` 让旧 Token 失效、前端改密后清本地凭证并回登录页。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 改密接口 | [`backend/app/api/user.py`](../../backend/app/api/user.py) | `update_password`（第 11 节已贴完整） |
| 输入模型 | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `UserPasswordUpdate`（第 09 节已贴） |
| 密码版本 | [`backend/app/utils/jwt.py`](../../backend/app/utils/jwt.py) + [`backend/app/dependencies/auth.py`](../../backend/app/dependencies/auth.py) | 第 06 节已贴完整 |
| 前端改密表单 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `savePassword`（完整页见附录） |

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中改密部分：

```js
const passwordForm = reactive({ old_password: '', new_password: '', confirmPassword: '' })
const validateNewPassword = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入新密码'))
  else if (value !== passwordForm.new_password) callback(new Error('两次输入的密码不一致'))
  else callback()
}
const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 8, max: 64, message: '密码长度为 8～64 个字符', trigger: 'blur' }],
  confirmPassword: [{ validator: validateNewPassword, trigger: 'blur' }]
}

const savePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await updatePasswordApi({ old_password: passwordForm.old_password, new_password: passwordForm.new_password })
    ElMessage.success('密码修改成功，请重新登录')
    clearLoginData()
    await router.replace('/login')
  } finally { savingValue.value = false }
}
```

**数据流：** 前端校验两次输入 → `updatePasswordApi` 发旧/新密码 → 后端验证旧密码 → 存新哈希 → 旧 JWT 的 `password_version` 失配 → 前端 `clearLoginData()` 并跳登录。

**验证：** 错误旧密码/新旧相同报 400；改密后旧 Token 请求 `/api/user/info` 返回 401，新密码重新登录成功。此操作真实改密，只对自己的练习账号执行。

## 第 13 节：管理员用户列表

**知识点清单：** `get_current_admin` 授权、`Query(ge/le)` 限制页码、`or_` 多字段模糊搜索、`count()` 总数 + `offset/limit` 分页、axios `params` 拼查询串、`el-table` + `el-pagination` 共享状态。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 列表接口 | [`backend/app/api/user.py`](../../backend/app/api/user.py) | `get_user_list`（第 11 节已贴完整） |
| 管理员授权 | [`backend/app/dependencies/permission.py`](../../backend/app/dependencies/permission.py) | `get_current_admin`（第 06 节已贴完整） |
| 列表 API | [`fronted/src/api/user.js`](../../fronted/src/api/user.js) | `getUserListApi`（第 10 节已贴完整） |
| 表格与分页 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `searchParams`、`loadUserList`（完整页见附录） |

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中列表部分（模板 + 逻辑）：

```vue
<el-tab-pane v-if="isAdmin" label="用户管理" name="manager">
  <div class="toolbar">
    <el-input v-model="searchParams.keyword" clearable placeholder="用户名、姓名或邮箱" style="width: 240px" @keyup.enter="loadUserList" @clear="loadUserList" />
    <el-button @click="loadUserList">查询</el-button>
    <el-button type="primary" @click="openUserDialog()">新增用户</el-button>
  </div>
  <el-table v-loading="loadingValue" :data="userList" stripe>
    <el-table-column prop="username" label="用户名" min-width="110" />
    <el-table-column prop="full_name" label="姓名" min-width="100" />
    <el-table-column prop="email" label="邮箱" min-width="190" />
    <el-table-column label="角色" width="100"><template #default="scope"><el-tag :type="scope.row.is_superuser ? 'danger' : 'success'">{{ scope.row.is_superuser ? '管理员' : '用户' }}</el-tag></template></el-table-column>
    <el-table-column label="状态" width="90"><template #default="scope"><el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '禁用' }}</el-tag></template></el-table-column>
    <el-table-column label="注册时间" min-width="170"><template #default="scope">{{ formatDate(scope.row.create_time) }}</template></el-table-column>
    <el-table-column label="操作" width="140" fixed="right"><template #default="scope"><el-button link type="primary" @click="openUserDialog(scope.row)">编辑</el-button><el-button link type="danger" @click="removeUser(scope.row)">删除</el-button></template></el-table-column>
  </el-table>
  <el-pagination v-model:current-page="searchParams.page" v-model:page-size="searchParams.page_size" layout="total, prev, pager, next" :total="userTotal" class="pagination" @current-change="loadUserList" />
</el-tab-pane>
```

```js
const userList = ref([])
const userTotal = ref(0)
const searchParams = reactive({ page: 1, page_size: 10, keyword: '' })

const loadUserList = async () => {
  loadingValue.value = true
  try {
    const res = await getUserListApi(searchParams)
    userList.value = res.data.list
    userTotal.value = res.data.total
  } finally { loadingValue.value = false }
}
```

**数据流：** `searchParams` 变化 → `getUserListApi` 把参数变成 URL 查询串 → 后端先授权再查总数和当前页 → `res.data.list` 驱动表格、`res.data.total` 驱动分页。

**验证：** 管理员按用户名/姓名/邮箱搜索、翻页，观察 Network 查询参数；普通用户 Token 请求 `GET /api/user` 得 403，不带 Token 得 401。

## 第 14 节：管理员用户增删改

**知识点清单：** `AdminUserCreate/AdminUserUpdate` 分建模、`model_dump(exclude_unset=True)` 局部更新、`model_fields_set` 区分“没传”与“传 null”、自我保护（不能禁用/降权/删除自己）、`IntegrityError` 兜底外键约束、对话框新增/编辑双模式。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 增删改接口 | [`backend/app/api/user.py`](../../backend/app/api/user.py) | `create_user`、`update_user`、`delete_user`（第 11 节已贴完整） |
| 增删改 Schema | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `AdminUserCreate`、`AdminUserUpdate`（第 09 节已贴完整） |
| 增删改 API | [`fronted/src/api/user.js`](../../fronted/src/api/user.js) | `createUserApi`、`updateUserApi`、`deleteUserApi`（第 10 节已贴完整） |
| 对话框双模式 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `openUserDialog`、`saveUser`、`removeUser`（完整页见附录） |

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中新增/编辑对话框模板：

```vue
<el-dialog v-model="userDialogVisible" :title="userForm.id ? '编辑用户' : '新增用户'" width="520px">
  <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
    <el-form-item label="用户名" prop="username"><el-input v-model="userForm.username" :disabled="Boolean(userForm.id)" /></el-form-item>
    <el-form-item v-if="!userForm.id" label="初始密码" prop="password"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
    <el-form-item label="姓名"><el-input v-model="userForm.full_name" /></el-form-item>
    <el-form-item label="邮箱" prop="email"><el-input v-model="userForm.email" /></el-form-item>
    <el-form-item label="管理员"><el-switch v-model="userForm.is_superuser" /></el-form-item>
    <el-form-item label="启用账号"><el-switch v-model="userForm.is_active" /></el-form-item>
  </el-form>
  <template #footer><el-button @click="userDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveUser">保存</el-button></template>
</el-dialog>
```

```js
const openUserDialog = (user = null) => {
  Object.assign(userForm, user ? { ...user, password: '' } : { id: null, username: '', password: '', full_name: '', email: '', is_active: true, is_superuser: false })
  userDialogVisible.value = true
}

const saveUser = async () => {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    if (userForm.id) {
      await updateUserApi(userForm.id, { email: userForm.email.trim(), full_name: userForm.full_name?.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser })
    } else {
      await createUserApi({ username: userForm.username.trim(), password: userForm.password, email: userForm.email.trim(), full_name: userForm.full_name.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser })
    }
    ElMessage.success(userForm.id ? '用户修改成功' : '用户新增成功')
    userDialogVisible.value = false
    await loadUserList()
  } finally { savingValue.value = false }
}

const removeUser = async (user) => {
  try {
    await ElMessageBox.confirm(`确定删除用户“${user.username}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // Element Plus 在用户取消或关闭确认框时会 reject，这是正常操作，直接结束即可。
    return
  }
  await deleteUserApi(user.id)
  ElMessage.success('删除成功')
  await loadUserList()
}
```

**数据流：** 打开对话框 → 表单校验 → POST 或 PUT → 后端校验身份/字段 → ORM `commit()` → 前端 `loadUserList()` 刷新。编辑时 `v-if="!userForm.id"` 使初始密码只在新增出现，编辑提交对象不含 `username/password`。

**验证：** 新增可搜索、编辑后刷新正确；编辑自己尝试禁用/降权得 400；取消删除确认框时 Network 无 DELETE；删除有预约记录的用户会因外键约束失败，改为禁用。

## 本组自检

用一张流程图串起 `UserCreate/AdminUserCreate → auth/user 路由 → get_current_user/get_current_admin → User ORM → UserResponse → src/api/user.js → user.vue`。解释三类数据去向：密码明文只短暂存在于请求、数据库存 bcrypt 哈希、响应不含密码。再回答：注册为什么不能指定管理员？上传为什么刷新后没有头像？改密为什么旧 Token 失效？前端隐藏管理页与接口权限有什么不同？

---

## 附录：`user.vue` 完整源码（本组第 10–14 节共用页面）

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 为纯 CSS 表现，省略）：

```vue
<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">{{ isAdmin ? '用户与个人中心' : '个人中心' }}</h1></div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="个人信息" name="profile">
        <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="90px" class="narrow-form">
          <el-form-item label="用户名"><el-input :model-value="userInfo?.username" disabled /></el-form-item>
          <el-form-item label="姓名" prop="full_name"><el-input v-model="profileForm.full_name" placeholder="请输入姓名" /></el-form-item>
          <el-form-item label="邮箱" prop="email"><el-input v-model="profileForm.email" placeholder="请输入邮箱" /></el-form-item>
          <el-form-item label="账号角色"><el-tag :type="isAdmin ? 'danger' : 'success'">{{ isAdmin ? '管理员' : '普通用户' }}</el-tag></el-form-item>
          <el-form-item><el-button type="primary" :loading="savingValue" @click="saveProfile">保存个人信息</el-button></el-form-item>
        </el-form>

        <el-divider content-position="left">文件上传接口演示</el-divider>
        <div class="upload-demo">
          <el-upload :auto-upload="false" :show-file-list="false" accept="image/jpeg,image/png,image/webp" :on-change="handleUploadChange">
            <el-button :loading="uploadingValue">选择并上传图片</el-button>
          </el-upload>
          <img v-if="uploadedImageUrl" :src="uploadedImageUrl" alt="上传预览" />
          <span v-else>支持 JPG、PNG、WEBP，最大 5MB</span>
        </div>
      </el-tab-pane>

      <el-tab-pane label="修改密码" name="password">
        <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px" class="narrow-form">
          <el-form-item label="原密码" prop="old_password"><el-input v-model="passwordForm.old_password" type="password" show-password /></el-form-item>
          <el-form-item label="新密码" prop="new_password"><el-input v-model="passwordForm.new_password" type="password" show-password /></el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword"><el-input v-model="passwordForm.confirmPassword" type="password" show-password /></el-form-item>
          <el-form-item><el-button type="primary" :loading="savingValue" @click="savePassword">修改密码</el-button></el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane v-if="isAdmin" label="用户管理" name="manager">
        <div class="toolbar">
          <el-input v-model="searchParams.keyword" clearable placeholder="用户名、姓名或邮箱" style="width: 240px" @keyup.enter="loadUserList" @clear="loadUserList" />
          <el-button @click="loadUserList">查询</el-button>
          <el-button type="primary" @click="openUserDialog()">新增用户</el-button>
        </div>
        <el-table v-loading="loadingValue" :data="userList" stripe>
          <el-table-column prop="username" label="用户名" min-width="110" />
          <el-table-column prop="full_name" label="姓名" min-width="100" />
          <el-table-column prop="email" label="邮箱" min-width="190" />
          <el-table-column label="角色" width="100"><template #default="scope"><el-tag :type="scope.row.is_superuser ? 'danger' : 'success'">{{ scope.row.is_superuser ? '管理员' : '用户' }}</el-tag></template></el-table-column>
          <el-table-column label="状态" width="90"><template #default="scope"><el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '禁用' }}</el-tag></template></el-table-column>
          <el-table-column label="注册时间" min-width="170"><template #default="scope">{{ formatDate(scope.row.create_time) }}</template></el-table-column>
          <el-table-column label="操作" width="140" fixed="right"><template #default="scope"><el-button link type="primary" @click="openUserDialog(scope.row)">编辑</el-button><el-button link type="danger" @click="removeUser(scope.row)">删除</el-button></template></el-table-column>
        </el-table>
        <el-pagination v-model:current-page="searchParams.page" v-model:page-size="searchParams.page_size" layout="total, prev, pager, next" :total="userTotal" class="pagination" @current-change="loadUserList" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="userDialogVisible" :title="userForm.id ? '编辑用户' : '新增用户'" width="520px">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-form-item label="用户名" prop="username"><el-input v-model="userForm.username" :disabled="Boolean(userForm.id)" /></el-form-item>
        <el-form-item v-if="!userForm.id" label="初始密码" prop="password"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="userForm.full_name" /></el-form-item>
        <el-form-item label="邮箱" prop="email"><el-input v-model="userForm.email" /></el-form-item>
        <el-form-item label="管理员"><el-switch v-model="userForm.is_superuser" /></el-form-item>
        <el-form-item label="启用账号"><el-switch v-model="userForm.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="userDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveUser">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { createUserApi, deleteUserApi, getUserListApi, updatePasswordApi, updateProfileApi, updateUserApi, uploadImageApi } from '@/api/user'
import { useUser } from '@/utils/user'

const router = useRouter()
const { userInfo, isAdmin, updateUser, clearLoginData } = useUser()
const activeTab = ref('profile')
const loadingValue = ref(false)
const savingValue = ref(false)
const uploadingValue = ref(false)
const uploadedImageUrl = ref('')
const userDialogVisible = ref(false)
const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const userFormRef = ref(null)
const userList = ref([])
const userTotal = ref(0)

const profileForm = reactive({ full_name: '', email: '' })
const passwordForm = reactive({ old_password: '', new_password: '', confirmPassword: '' })
const searchParams = reactive({ page: 1, page_size: 10, keyword: '' })
const userForm = reactive({ id: null, username: '', password: '', full_name: '', email: '', is_active: true, is_superuser: false })

const profileRules = { email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }] }
const validateNewPassword = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入新密码'))
  else if (value !== passwordForm.new_password) callback(new Error('两次输入的密码不一致'))
  else callback()
}
const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 8, max: 64, message: '密码长度为 8～64 个字符', trigger: 'blur' }],
  confirmPassword: [{ validator: validateNewPassword, trigger: 'blur' }]
}
const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, max: 20, message: '长度为 3～20 个字符', trigger: 'blur' }],
  password: [{ required: true, message: '请输入初始密码', trigger: 'blur' }, { min: 8, max: 64, message: '长度为 8～64 个字符', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }]
}

const saveProfile = async () => {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const res = await updateProfileApi({ email: profileForm.email.trim(), full_name: profileForm.full_name.trim() || null })
    updateUser(res.data)
    ElMessage.success('个人信息修改成功')
  } finally { savingValue.value = false }
}

const savePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await updatePasswordApi({ old_password: passwordForm.old_password, new_password: passwordForm.new_password })
    ElMessage.success('密码修改成功，请重新登录')
    clearLoginData()
    await router.replace('/login')
  } finally { savingValue.value = false }
}

const handleUploadChange = async (uploadFile) => {
  if (!uploadFile.raw) return
  uploadingValue.value = true
  try {
    const res = await uploadImageApi(uploadFile.raw)
    uploadedImageUrl.value = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}${res.data.url}`
    ElMessage.success('图片上传成功')
  } finally { uploadingValue.value = false }
}

const loadUserList = async () => {
  loadingValue.value = true
  try {
    const res = await getUserListApi(searchParams)
    userList.value = res.data.list
    userTotal.value = res.data.total
  } finally { loadingValue.value = false }
}

const openUserDialog = (user = null) => {
  Object.assign(userForm, user ? { ...user, password: '' } : { id: null, username: '', password: '', full_name: '', email: '', is_active: true, is_superuser: false })
  userDialogVisible.value = true
}

const saveUser = async () => {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    if (userForm.id) {
      await updateUserApi(userForm.id, { email: userForm.email.trim(), full_name: userForm.full_name?.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser })
    } else {
      await createUserApi({ username: userForm.username.trim(), password: userForm.password, email: userForm.email.trim(), full_name: userForm.full_name.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser })
    }
    ElMessage.success(userForm.id ? '用户修改成功' : '用户新增成功')
    userDialogVisible.value = false
    await loadUserList()
  } finally { savingValue.value = false }
}

const removeUser = async (user) => {
  try {
    await ElMessageBox.confirm(`确定删除用户“${user.username}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // Element Plus 在用户取消或关闭确认框时会 reject，这是正常操作，直接结束即可。
    return
  }
  await deleteUserApi(user.id)
  ElMessage.success('删除成功')
  await loadUserList()
}

const formatDate = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'

onMounted(async () => {
  Object.assign(profileForm, { full_name: userInfo.value?.full_name || '', email: userInfo.value?.email || '' })
  if (isAdmin.value) await loadUserList()
})
</script>
```
