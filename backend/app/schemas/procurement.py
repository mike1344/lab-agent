from typing import Literal

from pydantic import BaseModel, Field


class ProcurementCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    quantity: int = Field(default=1, ge=1, le=1000)
    # 验收时才强制要求关联设备；申请阶段可以先不选
    equipment_id: int | None = None
    remark: str | None = Field(default=None, max_length=255)


class ProcurementUpdate(BaseModel):
    """状态流转：pending -> arrived -> accepted；不接受跨级或回退。"""

    status: Literal["arrived", "accepted"]
    equipment_id: int | None = None
    remark: str | None = Field(default=None, max_length=255)
