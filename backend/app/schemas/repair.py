from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RepairCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=2, max_length=2000)
    lab_id: int | None = None
    equipment_id: int | None = None


class RepairHandle(BaseModel):
    """管理员处理报修：更新状态 + 填写处理备注。"""
    status: str  # processing / resolved
    handle_comment: str | None = Field(default=None, max_length=500)


class RepairResponse(BaseModel):
    id: int
    reporter_id: int
    reporter_name: str
    lab_id: int | None
    lab_name: str | None
    equipment_id: int | None
    equipment_name: str | None
    title: str
    description: str
    status: str
    handle_comment: str | None
    handler_id: int | None
    handler_name: str | None
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)
