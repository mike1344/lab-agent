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
