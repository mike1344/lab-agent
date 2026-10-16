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
