# 第 15–19 节：实验室、设备与预约业务（知识点 ↔ 完整代码对照）

> 本份是「**知识点 ↔ 完整代码**」对照版。业务部分每节课的模型、Schema、路由、前端页面都按**当前项目完整源码**贴出（含 import；Vue 页面含完整 `<template>` 与 `<script setup>`，仅 `<style scoped>` 纯 CSS 省略）。第 17 节讲角色渲染，复用第 15、16 节的完整页面，不重复贴整页，只补关键分支与布局联动。

## 第 15 节：开发实验室管理功能

**知识点清单：** `Lab` ORM 实体与字段约束、`LabCreate/LabUpdate/LabResponse` 区分输入输出、`field_validator` 去空白、`model_validator` 拒绝把必填列设为 null、管理员增删改 / 登录用户查询、`status=1/0` 开放与暂停、`only_open` 查询过滤、外键约束导致删除受限、前端 `el-table` + 对话框表单。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 数据表与状态字段 | [`backend/app/models/lab.py`](../../backend/app/models/lab.py) | `class Lab(Base)`、`status` |
| 输入/输出模型 | [`backend/app/schemas/lab.py`](../../backend/app/schemas/lab.py) | `LabBase/LabCreate/LabUpdate/LabResponse` |
| 查询与增删改 | [`backend/app/api/lab.py`](../../backend/app/api/lab.py) | `get_lab_list/create_lab/update_lab/delete_lab` |
| 前端接口 | [`fronted/src/api/lab.js`](../../fronted/src/api/lab.js) | 四个 API 函数 |
| 实验室页面 | [`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue) | 完整组件（见下） |

**完整源码：**

[`backend/app/models/lab.py`](../../backend/app/models/lab.py)（当前完整内容）：

```python
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lab(Base):
    """实验室基础信息。"""

    __tablename__ = "labs"
    __table_args__ = {"comment": "实验室表"}

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 1 表示开放预约，0 表示暂停使用。
    status: Mapped[int] = mapped_column(default=1, nullable=False)
```

[`backend/app/schemas/lab.py`](../../backend/app/schemas/lab.py)（当前完整内容）：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LabBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=200)
    capacity: int = Field(default=1, ge=1, le=1000)
    description: str | None = None
    status: int = Field(default=1, ge=0, le=1)

    @field_validator("name", "location")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """先去掉两端空格，再检查真正可见的字符数。"""
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned


class LabCreate(LabBase):
    pass


class LabUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    location: str | None = Field(default=None, min_length=2, max_length=200)
    capacity: int | None = Field(default=None, ge=1, le=1000)
    description: str | None = None
    status: int | None = Field(default=None, ge=0, le=1)

    @field_validator("name", "location")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        # PATCH 风格更新允许省略字段，但不能把数据库里的必填列显式改成 null。
        required_fields = ("name", "location", "capacity", "status")
        if any(field in self.model_fields_set and getattr(self, field) is None for field in required_fields):
            raise ValueError("实验室必填字段不能设为 null")
        return self


class LabResponse(LabBase):
    id: int
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

[`backend/app/api/lab.py`](../../backend/app/api/lab.py)（当前完整内容）：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.lab import Lab
from app.models.user import User
from app.schemas.lab import LabCreate, LabResponse, LabUpdate

router = APIRouter(prefix="/labs", tags=["实验室管理"])


@router.get("")
def get_lab_list(
    keyword: str = "",
    only_open: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询实验室列表；学生端通过 only_open 只展示开放实验室。"""
    query = db.query(Lab)
    if keyword.strip():
        query = query.filter(Lab.name.like(f"%{keyword.strip()}%"))
    if only_open:
        query = query.filter(Lab.status == 1)
    labs = query.order_by(Lab.id.desc()).all()
    return Response.success(data=[LabResponse.model_validate(lab) for lab in labs])


@router.post("")
def create_lab(
    data: LabCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if db.query(Lab).filter(Lab.name == data.name.strip()).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室名称已存在")
    lab = Lab(**data.model_dump())
    lab.name = lab.name.strip()
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return Response.success(message="实验室新增成功", data=LabResponse.model_validate(lab))


@router.put("/{lab_id}")
def update_lab(
    lab_id: int,
    data: LabUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lab = db.get(Lab, lab_id)
    if not lab:
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("name"):
        update_data["name"] = update_data["name"].strip()
        exists = db.query(Lab).filter(Lab.name == update_data["name"], Lab.id != lab_id).first()
        if exists:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室名称已存在")
    for field, value in update_data.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return Response.success(message="实验室修改成功", data=LabResponse.model_validate(lab))


@router.delete("/{lab_id}")
def delete_lab(
    lab_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lab = db.get(Lab, lab_id)
    if not lab:
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    db.delete(lab)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="实验室已有设备或预约记录，请改为暂停开放",
        )
    return Response.success(message="实验室删除成功")
```

[`fronted/src/api/lab.js`](../../fronted/src/api/lab.js)（当前完整内容；被第 15、17、18、19 节共用）：

```js
import request from '@/utils/request'

export function getLabListApi(params) {
  return request.get('/api/labs', { params })
}

export function createLabApi(data) {
  return request.post('/api/labs', data)
}

export function updateLabApi(labId, data) {
  return request.put(`/api/labs/${labId}`, data)
}

export function deleteLabApi(labId) {
  return request.delete(`/api/labs/${labId}`)
}
```

[`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 只有一行对话框间距，省略）：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '实验室管理' : '可预约实验室' }}</h1>
      <el-button v-if="isAdmin" type="primary" @click="openLabDialog()">新增实验室</el-button>
    </div>
    <div class="toolbar">
      <el-input v-model="keyword" clearable placeholder="搜索实验室名称" style="width: 240px" @keyup.enter="loadLabList" @clear="loadLabList" />
      <el-button @click="loadLabList">查询</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="labList" stripe>
      <el-table-column prop="name" label="实验室名称" min-width="150" />
      <el-table-column prop="location" label="位置" min-width="160" />
      <el-table-column prop="capacity" label="容纳人数" width="100" />
      <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="scope.row.status === 1 ? 'success' : 'info'">{{ scope.row.status === 1 ? '开放' : '暂停' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" :width="isAdmin ? 250 : 180" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="showEquipment(scope.row)">查看设备</el-button>
          <template v-if="isAdmin">
            <el-button link type="primary" @click="openLabDialog(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="removeLab(scope.row)">删除</el-button>
          </template>
          <el-button v-else link type="success" @click="openReservationDialog(scope.row)">立即预约</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="labDialogVisible" :title="labForm.id ? '编辑实验室' : '新增实验室'" width="520px">
      <el-form ref="labFormRef" :model="labForm" :rules="labRules" label-width="90px">
        <el-form-item label="名称" prop="name"><el-input v-model="labForm.name" /></el-form-item>
        <el-form-item label="位置" prop="location"><el-input v-model="labForm.location" /></el-form-item>
        <el-form-item label="容纳人数" prop="capacity"><el-input-number v-model="labForm.capacity" :min="1" :max="1000" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="labForm.status" :active-value="1" :inactive-value="0" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="labForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="labDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveLab">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="reservationDialogVisible" title="提交实验室预约" width="520px">
      <el-alert :title="`正在预约：${selectedLab?.name || ''}`" type="info" :closable="false" />
      <el-form ref="reservationFormRef" :model="reservationForm" :rules="reservationRules" label-width="90px" class="dialog-form">
        <el-form-item label="预约日期" prop="reservation_date"><el-date-picker v-model="reservationForm.reservation_date" type="date" value-format="YYYY-MM-DD" :disabled-date="disablePastDate" style="width: 100%" /></el-form-item>
        <el-form-item label="预约时间" prop="timeRange"><el-time-picker v-model="reservationForm.timeRange" is-range value-format="HH:mm:ss" range-separator="至" start-placeholder="开始时间" end-placeholder="结束时间" style="width: 100%" /></el-form-item>
        <el-form-item label="预约用途" prop="purpose"><el-input v-model="reservationForm.purpose" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="reservationDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveReservation">提交申请</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { createLabApi, deleteLabApi, getLabListApi, updateLabApi } from '@/api/lab'
import { createReservationApi } from '@/api/reservation'
import { useUser } from '@/utils/user'

const router = useRouter()
const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const keyword = ref('')
const labList = ref([])
const labDialogVisible = ref(false)
const reservationDialogVisible = ref(false)
const labFormRef = ref(null)
const reservationFormRef = ref(null)
const selectedLab = ref(null)
const labForm = reactive({ id: null, name: '', location: '', capacity: 1, description: '', status: 1 })
const reservationForm = reactive({ reservation_date: '', timeRange: [], purpose: '' })

const labRules = {
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  location: [{ required: true, message: '请输入实验室位置', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容纳人数', trigger: 'change' }]
}
const reservationRules = {
  reservation_date: [{ required: true, message: '请选择预约日期', trigger: 'change' }],
  timeRange: [{ type: 'array', required: true, len: 2, message: '请选择预约时间', trigger: 'change' }],
  purpose: [{ required: true, message: '请填写预约用途', trigger: 'blur' }]
}

const loadLabList = async () => {
  loadingValue.value = true
  try {
    const res = await getLabListApi({ keyword: keyword.value, only_open: !isAdmin.value })
    labList.value = res.data
  } finally { loadingValue.value = false }
}

const openLabDialog = (lab = null) => {
  Object.assign(labForm, lab || { id: null, name: '', location: '', capacity: 1, description: '', status: 1 })
  labDialogVisible.value = true
}

const saveLab = async () => {
  const valid = await labFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = { name: labForm.name.trim(), location: labForm.location.trim(), capacity: labForm.capacity, description: labForm.description || null, status: labForm.status }
    if (labForm.id) await updateLabApi(labForm.id, data)
    else await createLabApi(data)
    ElMessage.success(labForm.id ? '实验室修改成功' : '实验室新增成功')
    labDialogVisible.value = false
    await loadLabList()
  } finally { savingValue.value = false }
}

const removeLab = async (lab) => {
  try {
    await ElMessageBox.confirm(`确定删除“${lab.name}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // 取消确认框属于正常分支，不应继续删除，也不向 Vue 抛出未处理异常。
    return
  }
  await deleteLabApi(lab.id)
  ElMessage.success('删除成功')
  await loadLabList()
}

const showEquipment = (lab) => router.push({ path: '/equ', query: { lab_id: lab.id } })
const openReservationDialog = (lab) => {
  selectedLab.value = lab
  Object.assign(reservationForm, { reservation_date: '', timeRange: [], purpose: '' })
  reservationDialogVisible.value = true
}
const disablePastDate = (date) => date.getTime() < new Date().setHours(0, 0, 0, 0)

const saveReservation = async () => {
  const valid = await reservationFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await createReservationApi({ lab_id: selectedLab.value.id, reservation_date: reservationForm.reservation_date, start_time: reservationForm.timeRange[0], end_time: reservationForm.timeRange[1], purpose: reservationForm.purpose.trim() })
    ElMessage.success('预约申请已提交')
    reservationDialogVisible.value = false
    await router.push('/reservation')
  } finally { savingValue.value = false }
}

onMounted(loadLabList)
</script>
```

**数据流：** 学生页面默认 `only_open: !isAdmin` → 后端按 `Lab.status == 1` 过滤；管理员 `only_open=false` 能看到暂停的实验室。`only_open` 是查询选项，不是学生端的强制数据权限。

**验证：** 管理员新增/改容量/暂停开放；学生默认看不到暂停实验室。删除有设备或预约的实验室会因外键约束返回 400，应改为暂停开放。

## 第 16 节：开发实验室设备管理

**知识点清单：** `lab_id` 外键归属实验室、`relationship("Lab")`、`joinedload(Equipment.lab)` 预加载避免 N+1、设备编号唯一、`status` + `quantity` 决定可用、`equipment_to_dict` 把关联实验室名一起返回、前端按实验室筛选。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 设备表与外键 | [`backend/app/models/equipment.py`](../../backend/app/models/equipment.py) | `lab_id = ForeignKey("labs.id")`、`lab = relationship("Lab")` |
| 输入/输出模型 | [`backend/app/schemas/equipment.py`](../../backend/app/schemas/equipment.py) | `EquipmentBase/Create/Update/Response` |
| 预加载与可用过滤 | [`backend/app/api/equipment.py`](../../backend/app/api/equipment.py) | `joinedload`、`only_available` |
| 前端接口 | [`fronted/src/api/equipment.js`](../../fronted/src/api/equipment.js) | 四个 API 函数 |
| 设备页面 | [`fronted/src/views/equ.vue`](../../fronted/src/views/equ.vue) | 完整组件（见下） |

**完整源码：**

[`backend/app/models/equipment.py`](../../backend/app/models/equipment.py)（当前完整内容）：

```python
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Equipment(Base):
    """实验室设备信息。"""

    __tablename__ = "equipment"
    __table_args__ = {"comment": "实验室设备表"}

    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 1 表示正常，0 表示停用或维护中。
    status: Mapped[int] = mapped_column(default=1, nullable=False)

    lab = relationship("Lab")
```

[`backend/app/schemas/equipment.py`](../../backend/app/schemas/equipment.py)（当前完整内容）：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EquipmentBase(BaseModel):
    lab_id: int
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=50)
    quantity: int = Field(default=1, ge=0, le=10000)
    description: str | None = None
    status: int = Field(default=1, ge=0, le=1)

    @field_validator("name", "code")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    lab_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=100)
    code: str | None = Field(default=None, min_length=2, max_length=50)
    quantity: int | None = Field(default=None, ge=0, le=10000)
    description: str | None = None
    status: int | None = Field(default=None, ge=0, le=1)

    @field_validator("name", "code")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required_fields = ("lab_id", "name", "code", "quantity", "status")
        if any(field in self.model_fields_set and getattr(self, field) is None for field in required_fields):
            raise ValueError("设备必填字段不能设为 null")
        return self


class EquipmentResponse(EquipmentBase):
    id: int
    lab_name: str | None = None
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

[`backend/app/api/equipment.py`](../../backend/app/api/equipment.py)（当前完整内容）：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.user import User
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate

router = APIRouter(prefix="/equipment", tags=["设备管理"])


def equipment_to_dict(equipment: Equipment) -> dict:
    """把关联的实验室名称一起整理给前端，避免前端再次请求。"""
    return {
        "id": equipment.id,
        "lab_id": equipment.lab_id,
        "lab_name": equipment.lab.name if equipment.lab else None,
        "name": equipment.name,
        "code": equipment.code,
        "quantity": equipment.quantity,
        "description": equipment.description,
        "status": equipment.status,
        "create_time": equipment.create_time,
        "update_time": equipment.update_time,
    }


@router.get("")
def get_equipment_list(
    lab_id: int | None = None,
    keyword: str = "",
    only_available: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Equipment).options(joinedload(Equipment.lab))
    if lab_id:
        query = query.filter(Equipment.lab_id == lab_id)
    if keyword.strip():
        query = query.filter(Equipment.name.like(f"%{keyword.strip()}%"))
    if only_available:
        query = query.filter(Equipment.status == 1, Equipment.quantity > 0)
    equipment_list = query.order_by(Equipment.id.desc()).all()
    return Response.success(data=[equipment_to_dict(item) for item in equipment_list])


@router.post("")
def create_equipment(
    data: EquipmentCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Lab, data.lab_id):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="所属实验室不存在")
    if db.query(Equipment).filter(Equipment.code == data.code.strip()).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="设备编号已存在")
    equipment = Equipment(**data.model_dump())
    equipment.name = equipment.name.strip()
    equipment.code = equipment.code.strip()
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return Response.success(message="设备新增成功", data=equipment_to_dict(equipment))


@router.put("/{equipment_id}")
def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise BusinessException(code=BizCode.NOT_FOUND, message="设备不存在")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("lab_id") and not db.get(Lab, update_data["lab_id"]):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="所属实验室不存在")
    if update_data.get("code"):
        update_data["code"] = update_data["code"].strip()
        exists = db.query(Equipment).filter(
            Equipment.code == update_data["code"], Equipment.id != equipment_id
        ).first()
        if exists:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="设备编号已存在")
    for field, value in update_data.items():
        setattr(equipment, field, value)
    db.commit()
    db.refresh(equipment)
    return Response.success(message="设备修改成功", data=equipment_to_dict(equipment))


@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise BusinessException(code=BizCode.NOT_FOUND, message="设备不存在")
    db.delete(equipment)
    db.commit()
    return Response.success(message="设备删除成功")
```

[`fronted/src/api/equipment.js`](../../fronted/src/api/equipment.js)（当前完整内容）：

```js
import request from '@/utils/request'

export function getEquipmentListApi(params) {
  return request.get('/api/equipment', { params })
}

export function createEquipmentApi(data) {
  return request.post('/api/equipment', data)
}

export function updateEquipmentApi(equipmentId, data) {
  return request.put(`/api/equipment/${equipmentId}`, data)
}

export function deleteEquipmentApi(equipmentId) {
  return request.delete(`/api/equipment/${equipmentId}`)
}
```

[`fronted/src/views/equ.vue`](../../fronted/src/views/equ.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 为空块，省略）：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '设备管理' : '实验室设备列表' }}</h1>
      <el-button v-if="isAdmin" type="primary" @click="openEquipmentDialog()">新增设备</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="selectedLabId" clearable placeholder="全部实验室" style="width: 200px" @change="loadEquipmentList">
        <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="搜索设备名称" style="width: 220px" @keyup.enter="loadEquipmentList" @clear="loadEquipmentList" />
      <el-button @click="loadEquipmentList">查询</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="equipmentList" stripe>
      <el-table-column prop="code" label="设备编号" min-width="120" />
      <el-table-column prop="name" label="设备名称" min-width="150" />
      <el-table-column prop="lab_name" label="所属实验室" min-width="150" />
      <el-table-column prop="quantity" label="数量" width="90" />
      <el-table-column prop="description" label="设备说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="scope.row.status === 1 ? 'success' : 'warning'">{{ scope.row.status === 1 ? '正常' : '维护中' }}</el-tag></template>
      </el-table-column>
      <el-table-column v-if="isAdmin" label="操作" width="150" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="openEquipmentDialog(scope.row)">编辑</el-button>
          <el-button link type="danger" @click="removeEquipment(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="equipmentForm.id ? '编辑设备' : '新增设备'" width="540px">
      <el-form ref="equipmentFormRef" :model="equipmentForm" :rules="equipmentRules" label-width="100px">
        <el-form-item label="所属实验室" prop="lab_id">
          <el-select v-model="equipmentForm.lab_id" style="width: 100%"><el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" /></el-select>
        </el-form-item>
        <el-form-item label="设备名称" prop="name"><el-input v-model="equipmentForm.name" /></el-form-item>
        <el-form-item label="设备编号" prop="code"><el-input v-model="equipmentForm.code" /></el-form-item>
        <el-form-item label="设备数量" prop="quantity"><el-input-number v-model="equipmentForm.quantity" :min="0" :max="10000" /></el-form-item>
        <el-form-item label="设备状态"><el-switch v-model="equipmentForm.status" :active-value="1" :inactive-value="0" active-text="正常" inactive-text="维护" /></el-form-item>
        <el-form-item label="设备说明"><el-input v-model="equipmentForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveEquipment">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import { createEquipmentApi, deleteEquipmentApi, getEquipmentListApi, updateEquipmentApi } from '@/api/equipment'
import { getLabListApi } from '@/api/lab'
import { useUser } from '@/utils/user'

const route = useRoute()
const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const dialogVisible = ref(false)
const equipmentFormRef = ref(null)
const labList = ref([])
const equipmentList = ref([])
const keyword = ref('')
const selectedLabId = ref(route.query.lab_id ? Number(route.query.lab_id) : null)
const equipmentForm = reactive({ id: null, lab_id: null, name: '', code: '', quantity: 1, description: '', status: 1 })

const equipmentRules = {
  lab_id: [{ required: true, message: '请选择所属实验室', trigger: 'change' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入设备编号', trigger: 'blur' }]
}

const loadLabs = async () => {
  const res = await getLabListApi()
  labList.value = res.data
}

const loadEquipmentList = async () => {
  loadingValue.value = true
  try {
    const res = await getEquipmentListApi({ lab_id: selectedLabId.value || undefined, keyword: keyword.value, only_available: !isAdmin.value })
    equipmentList.value = res.data
  } finally { loadingValue.value = false }
}

const openEquipmentDialog = (equipment = null) => {
  Object.assign(equipmentForm, equipment || { id: null, lab_id: selectedLabId.value || labList.value[0]?.id || null, name: '', code: '', quantity: 1, description: '', status: 1 })
  dialogVisible.value = true
}

const saveEquipment = async () => {
  const valid = await equipmentFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = { lab_id: equipmentForm.lab_id, name: equipmentForm.name.trim(), code: equipmentForm.code.trim(), quantity: equipmentForm.quantity, description: equipmentForm.description || null, status: equipmentForm.status }
    if (equipmentForm.id) await updateEquipmentApi(equipmentForm.id, data)
    else await createEquipmentApi(data)
    ElMessage.success(equipmentForm.id ? '设备修改成功' : '设备新增成功')
    dialogVisible.value = false
    await loadEquipmentList()
  } finally { savingValue.value = false }
}

const removeEquipment = async (equipment) => {
  try {
    await ElMessageBox.confirm(`确定删除设备“${equipment.name}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // 用户点击“取消”或关闭弹窗时，Element Plus 会 reject 这个 Promise。
    return
  }
  await deleteEquipmentApi(equipment.id)
  ElMessage.success('删除成功')
  await loadEquipmentList()
}

onMounted(async () => {
  await loadLabs()
  await loadEquipmentList()
})
</script>
```

**数据流：** `joinedload(Equipment.lab)` 一次查询就带出实验室，`equipment_to_dict` 把 `lab_name` 一起返回，列表不再逐行查库。`only_available` 同时过滤 `status == 1` 和 `quantity > 0`；注意它**只检查设备自身**，不再检查所属实验室是否开放。

**验证：** 给一个实验室加两件设备，按实验室筛选；把其中一件数量改为 0，对比管理员与学生默认列表；重复设备编号报 400。

## 第 17 节：学生端与管理端的角色渲染

**知识点清单：** 一个页面按 `isAdmin` 呈现两套操作、`v-if` 展示逻辑与后端 `get_current_admin` 写权限的区别、学生端默认 `only_open`/`only_available`、布局菜单按角色换文案。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 共享角色状态 | [`fronted/src/utils/user.js`](../../fronted/src/utils/user.js) | `isAdmin = computed(...)`（第 03 节已贴完整） |
| 菜单按角色换文案 | [`fronted/src/layouts/layouts.vue`](../../fronted/src/layouts/layouts.vue) | 第 02 节已贴完整 |
| 学生默认只查开放实验室 | [`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue) | `only_open: !isAdmin.value`（第 15 节完整） |
| 学生默认只查可用设备 | [`fronted/src/views/equ.vue`](../../fronted/src/views/equ.vue) | `only_available: !isAdmin.value`（第 16 节完整） |

**关键分支源码**（完整页面见第 15、16 节）：

```js
// views/lab.vue：学生默认只请求开放实验室
const res = await getLabListApi({ keyword: keyword.value, only_open: !isAdmin.value })
```

```js
// views/equ.vue：学生默认只请求可用设备
const res = await getEquipmentListApi({ lab_id: selectedLabId.value || undefined, keyword: keyword.value, only_available: !isAdmin.value })
```

```vue
<!-- views/lab.vue：管理员显示编辑/删除，学生显示“立即预约” -->
<template v-if="isAdmin">
  <el-button link type="primary" @click="openLabDialog(scope.row)">编辑</el-button>
  <el-button link type="danger" @click="removeLab(scope.row)">删除</el-button>
</template>
<el-button v-else link type="success" @click="openReservationDialog(scope.row)">立即预约</el-button>
```

**数据流：** `isAdmin` 来自共享 `userInfo`（登录时写入、布局 `onMounted` 又向后端确认一次）→ 决定菜单文案、按钮显隐与查询参数。但**写接口的权限由后端 `Depends(get_current_admin)` 决定**，隐藏按钮只是体验。

**验证：** 分别用学生和管理员登录，记录同一页面的标题、按钮与数据差别；用普通用户 Token 直接 `POST /api/labs`，后端仍返回 403。

## 第 18 节：开发实验室预约功能

**知识点清单：** 预约请求字段、`model_validator` 校验开始早于结束、Service 统一承担开放状态/未来时间/时间冲突/写入、半开区间冲突公式、`with_for_update()` 行锁处理并发、普通接口与 AI 工具共用同一 Service。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 预约表与状态 | [`backend/app/models/reservation.py`](../../backend/app/models/reservation.py) | `Reservation`、`status` |
| 请求模型与时间校验 | [`backend/app/schemas/reservation.py`](../../backend/app/schemas/reservation.py) | `ReservationCreate.validate_time_range` |
| 业务规则与冲突检查 | [`backend/app/services/reservation.py`](../../backend/app/services/reservation.py) | `create_reservation_record` |
| 预约接口 | [`backend/app/api/reservation.py`](../../backend/app/api/reservation.py) | `create_reservation` 等 |
| 前端接口 | [`fronted/src/api/reservation.js`](../../fronted/src/api/reservation.js) | 五个 API 函数 |
| 提交表单 | [`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue) | `saveReservation`（第 15 节完整） |

**完整源码：**

[`backend/app/models/reservation.py`](../../backend/app/models/reservation.py)（当前完整内容）：

```python
from datetime import date, time

from sqlalchemy import Date, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Reservation(Base):
    """学生提交的实验室预约申请。"""

    __tablename__ = "reservations"
    __table_args__ = {"comment": "实验室预约表"}

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True)
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    # pending / approved / rejected / cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    review_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user = relationship("User")
    lab = relationship("Lab")
```

[`backend/app/schemas/reservation.py`](../../backend/app/schemas/reservation.py)（当前完整内容）：

```python
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReservationCreate(BaseModel):
    lab_id: int
    reservation_date: date
    start_time: time
    end_time: time
    purpose: str = Field(min_length=2, max_length=1000)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self


class ReservationReview(BaseModel):
    status: str
    review_comment: str | None = Field(default=None, max_length=500)


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    lab_id: int
    lab_name: str
    reservation_date: date
    start_time: time
    end_time: time
    purpose: str
    status: str
    review_comment: str | None = None
    create_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

[`backend/app/services/reservation.py`](../../backend/app/services/reservation.py)（当前完整内容；普通接口与 AI 工具共用的唯一写入口）：

```python
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate


def create_reservation_record(
    db: Session,
    user_id: int,
    data: ReservationCreate,
) -> Reservation:
    """创建预约的唯一业务入口，供普通接口和 AI Tool Calling 共用。

    先锁定实验室行，再检查时间冲突。MySQL/InnoDB 会让同一实验室的并发请求
    依次完成“检查 + 新增”，避免两个请求同时查到无冲突后都写入数据库。
    SQLite 测试环境会忽略 ``FOR UPDATE``，但仍可验证其余业务规则。
    """
    lab = (
        db.query(Lab)
        .filter(Lab.id == data.lab_id)
        .with_for_update()
        .first()
    )
    if not lab or lab.status != 1:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="实验室不存在或未开放",
        )
    now = datetime.now()
    if data.reservation_date < now.date():
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="不能预约过去的日期",
        )
    if data.reservation_date == now.date() and data.start_time <= now.time():
        # 日期是今天时还要检查开始时间；否则会生成无法按时使用的待审核预约。
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="预约开始时间必须晚于当前时间",
        )

    # 两个半开时间段 [start, end) 相交的充要条件：旧开始 < 新结束 且旧结束 > 新开始。
    conflict = db.query(Reservation).filter(
        Reservation.lab_id == data.lab_id,
        Reservation.reservation_date == data.reservation_date,
        Reservation.status.in_(["pending", "approved"]),
        Reservation.start_time < data.end_time,
        Reservation.end_time > data.start_time,
    ).first()
    if conflict:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="该时间段已有预约，请选择其他时间",
        )

    reservation = Reservation(
        user_id=user_id,
        status="pending",
        **data.model_dump(),
    )
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError as exc:
        # 数据库约束是最后一道保护；回滚后 Session 才能继续安全使用。
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="预约创建失败，请确认用户和实验室信息",
        ) from exc
    db.refresh(reservation)
    return reservation
```

[`backend/app/api/reservation.py`](../../backend/app/api/reservation.py)（当前完整内容；第 19 节的列表/审核也在此文件）：

```python
from fastapi import APIRouter, Depends
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationReview
from app.services.reservation import create_reservation_record

router = APIRouter(prefix="/reservations", tags=["实验室预约"])


def reservation_to_dict(reservation: Reservation) -> dict:
    """将预约及其关联对象转换成前端直接可展示的数据。"""
    return {
        "id": reservation.id,
        "user_id": reservation.user_id,
        "user_name": reservation.user.full_name or reservation.user.username,
        "lab_id": reservation.lab_id,
        "lab_name": reservation.lab.name,
        "reservation_date": reservation.reservation_date,
        "start_time": reservation.start_time,
        "end_time": reservation.end_time,
        "purpose": reservation.purpose,
        "status": reservation.status,
        "review_comment": reservation.review_comment,
        "create_time": reservation.create_time,
    }


def reservation_query(db: Session):
    """所有预约查询统一预加载用户与实验室，防止列表出现 N+1 查询。"""
    return db.query(Reservation).options(
        joinedload(Reservation.user), joinedload(Reservation.lab)
    )


@router.post("")
def create_reservation(
    data: ReservationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生提交预约，初始状态为待审核。"""
    reservation = create_reservation_record(db, current_user.id, data)
    # 重新读取一次以加载 user 和 lab 关联信息。
    reservation = reservation_query(db).filter(Reservation.id == reservation.id).first()
    return Response.success(message="预约申请已提交", data=reservation_to_dict(reservation))


@router.get("/mine")
def get_my_reservations(
    status: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = reservation_query(db).filter(Reservation.user_id == current_user.id)
    if status:
        query = query.filter(Reservation.status == status)
    items = query.order_by(Reservation.id.desc()).all()
    return Response.success(data=[reservation_to_dict(item) for item in items])


@router.put("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 与管理员审核锁定同一条预约行，避免双方同时读取 pending 后互相覆盖结果。
    reservation = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id)
        .with_for_update()
        .first()
    )
    if not reservation or reservation.user_id != current_user.id:
        raise BusinessException(code=BizCode.NOT_FOUND, message="预约记录不存在")
    if reservation.status not in ("pending", "approved"):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="当前状态不能取消")
    reservation.status = "cancelled"
    db.commit()
    return Response.success(message="预约已取消")


@router.get("")
def get_reservation_list(
    status: str = "",
    lab_id: int | None = None,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员查看全部预约，并可按状态和实验室筛选。"""
    query = reservation_query(db)
    if status:
        query = query.filter(Reservation.status == status)
    if lab_id:
        query = query.filter(Reservation.lab_id == lab_id)
    items = query.order_by(Reservation.id.desc()).all()
    return Response.success(data=[reservation_to_dict(item) for item in items])


@router.put("/{reservation_id}/review")
def review_reservation(
    reservation_id: int,
    data: ReservationReview,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员审核预约，只允许通过或拒绝。"""
    if data.status not in ("approved", "rejected"):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="审核状态不正确")
    reservation = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id)
        .with_for_update()
        .first()
    )
    if not reservation:
        raise BusinessException(code=BizCode.NOT_FOUND, message="预约记录不存在")
    if reservation.status != "pending":
        raise BusinessException(code=BizCode.BAD_REQUEST, message="该预约已经处理")

    if data.status == "approved":
        # 从提交到审核期间，日期可能已经过去，实验室也可能被管理员暂停开放。
        # 审核前复核一次，避免批准已经无法履行的预约。
        now = datetime.now()
        if reservation.reservation_date < now.date() or (
            reservation.reservation_date == now.date()
            and reservation.start_time <= now.time()
        ):
            raise BusinessException(code=BizCode.BAD_REQUEST, message="预约时间已经过去，不能通过审核")
        lab = db.query(Lab).filter(Lab.id == reservation.lab_id).with_for_update().first()
        if not lab or lab.status != 1:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室当前未开放，不能通过审核")

    reservation.status = data.status
    reservation.review_comment = data.review_comment
    db.commit()
    return Response.success(message="预约审核完成")
```

[`fronted/src/api/reservation.js`](../../fronted/src/api/reservation.js)（当前完整内容；被第 18、19 节共用）：

```js
import request from '@/utils/request'

export function createReservationApi(data) {
  return request.post('/api/reservations', data)
}

export function getMyReservationListApi(params) {
  return request.get('/api/reservations/mine', { params })
}

export function cancelReservationApi(reservationId) {
  return request.put(`/api/reservations/${reservationId}/cancel`)
}

export function getReservationListApi(params) {
  return request.get('/api/reservations', { params })
}

export function reviewReservationApi(reservationId, data) {
  return request.put(`/api/reservations/${reservationId}/review`, data)
}
```

**冲突公式推演：** 两个半开区间 `[s1,e1)` 与 `[s2,e2)` 相交 ⇔ `s1 < e2` 且 `s2 < e1`。所以“前一单结束恰好等于下一单开始”（`e1 == s2`）不冲突，可以相邻；完全重叠和部分重叠都满足公式，均被判冲突。`pending` 与 `approved` 都占用时段。

**验证：** 提交完全重叠、部分重叠、相邻三种情况，前两种报 400、最后一种成功。MySQL 下创建预约还会 `with_for_update()` 锁实验室行处理并发；SQLite 测试忽略该锁。注意当前前端只给学生显示预约按钮，但后端创建接口允许**任意已登录用户**调用。

## 第 19 节：我的预约与预约审核

**知识点清单：** 状态机 `pending/approved/rejected/cancelled`、学生只看自己、管理员看全部、取消与审核锁同一预约行、审核前复核状态与时间、`joinedload` 预加载、前端表格按状态渲染不同按钮。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 状态与列表/审核接口 | [`backend/app/api/reservation.py`](../../backend/app/api/reservation.py) | `get_my_reservations`、`get_reservation_list`、`cancel_reservation`、`review_reservation`（第 18 节已贴完整） |
| 前端接口 | [`fronted/src/api/reservation.js`](../../fronted/src/api/reservation.js) | 五个 API 函数（第 18 节已贴完整） |
| 预约页面 | [`fronted/src/views/reservation.vue`](../../fronted/src/views/reservation.vue) | 完整组件（见下） |

[`fronted/src/views/reservation.vue`](../../fronted/src/views/reservation.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 只有一行“已处理”灰字，省略）：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '预约审核' : '我的预约' }}</h1>
      <el-button v-if="!isAdmin" type="primary" @click="$router.push('/lab')">发起预约</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="statusValue" clearable placeholder="全部状态" style="width: 160px" @change="loadReservationList">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-if="isAdmin" v-model="selectedLabId" clearable placeholder="全部实验室" style="width: 190px" @change="loadReservationList">
        <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-button @click="loadReservationList">刷新</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="reservationList" stripe>
      <el-table-column v-if="isAdmin" prop="user_name" label="预约人" min-width="110" />
      <el-table-column prop="lab_name" label="实验室" min-width="140" />
      <el-table-column prop="reservation_date" label="预约日期" width="120" />
      <el-table-column label="预约时间" width="150">
        <template #default="scope">{{ formatTime(scope.row.start_time) }} - {{ formatTime(scope.row.end_time) }}</template>
      </el-table-column>
      <el-table-column prop="purpose" label="用途" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="statusMap[scope.row.status]?.type">{{ statusMap[scope.row.status]?.label || scope.row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="review_comment" label="审核意见" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="scope">
          <template v-if="isAdmin && scope.row.status === 'pending'">
            <el-button link type="success" @click="openReviewDialog(scope.row, 'approved')">通过</el-button>
            <el-button link type="danger" @click="openReviewDialog(scope.row, 'rejected')">拒绝</el-button>
          </template>
          <el-button v-else-if="!isAdmin && ['pending', 'approved'].includes(scope.row.status)" link type="danger" @click="cancelReservation(scope.row)">取消预约</el-button>
          <span v-else class="operation-finished">已处理</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="reviewDialogVisible" :title="reviewForm.status === 'approved' ? '通过预约' : '拒绝预约'" width="460px">
      <el-form label-position="top">
        <el-form-item label="审核意见">
          <el-input v-model="reviewForm.review_comment" type="textarea" :rows="4" :placeholder="reviewForm.status === 'rejected' ? '建议填写拒绝原因' : '可填写使用注意事项'" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="reviewDialogVisible = false">取消</el-button><el-button :type="reviewForm.status === 'approved' ? 'success' : 'danger'" :loading="savingValue" @click="saveReview">确认</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLabListApi } from '@/api/lab'
import { cancelReservationApi, getMyReservationListApi, getReservationListApi, reviewReservationApi } from '@/api/reservation'
import { useUser } from '@/utils/user'

const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const statusValue = ref('')
const selectedLabId = ref(null)
const labList = ref([])
const reservationList = ref([])
const reviewDialogVisible = ref(false)
const selectedReservation = ref(null)
const reviewForm = reactive({ status: 'approved', review_comment: '' })

const statusOptions = [
  { label: '待审核', value: 'pending' }, { label: '已通过', value: 'approved' },
  { label: '已拒绝', value: 'rejected' }, { label: '已取消', value: 'cancelled' }
]
const statusMap = {
  pending: { label: '待审核', type: 'warning' }, approved: { label: '已通过', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' }, cancelled: { label: '已取消', type: 'info' }
}

const loadReservationList = async () => {
  loadingValue.value = true
  try {
    const params = { status: statusValue.value, lab_id: selectedLabId.value || undefined }
    const res = isAdmin.value ? await getReservationListApi(params) : await getMyReservationListApi(params)
    reservationList.value = res.data
  } finally { loadingValue.value = false }
}

const formatTime = (value) => value?.slice(0, 5) || '--:--'
const openReviewDialog = (reservation, status) => {
  selectedReservation.value = reservation
  Object.assign(reviewForm, { status, review_comment: '' })
  reviewDialogVisible.value = true
}

const saveReview = async () => {
  savingValue.value = true
  try {
    await reviewReservationApi(selectedReservation.value.id, reviewForm)
    ElMessage.success('预约审核完成')
    reviewDialogVisible.value = false
    await loadReservationList()
  } finally { savingValue.value = false }
}

const cancelReservation = async (reservation) => {
  try {
    await ElMessageBox.confirm('确定取消这条预约吗？', '取消确认', { type: 'warning' })
  } catch {
    // 关闭确认框表示保留预约，直接返回，避免产生未处理的 Promise 拒绝。
    return
  }
  await cancelReservationApi(reservation.id)
  ElMessage.success('预约已取消')
  await loadReservationList()
}

onMounted(async () => {
  if (isAdmin.value) {
    const res = await getLabListApi()
    labList.value = res.data
  }
  await loadReservationList()
})
</script>
```

**数据流：** 学生进入页面 → `getMyReservationListApi` 只返回 `user_id == current_user.id` 的记录；管理员走 `getReservationListApi` 看全部。审核时后端先 `with_for_update()` 锁行，再检查 `status == "pending"`，“通过”还要复核时间未过、实验室仍开放。状态变化后前端旧按钮隐藏只是体验，后端每次仍重新校验。

**验证：** 走“学生提交 → 管理员通过 → 学生查看”；再测拒绝、取消、重复审核（第二次应报 400 “该预约已经处理”）。

## 本组自检

- 能画出预约的 `pending → approved/rejected` 与可取消状态，并用半开区间公式证明时间冲突判断。
- 能说明为什么普通接口与 AI 工具必须调用同一个 `create_reservation_record`。
- 能解释 `joinedload` 解决了什么、`with_for_update()` 在 MySQL 与 SQLite 的差别。
- 能指出 `only_open`、`only_available` 是查询选项而非强制数据权限。
