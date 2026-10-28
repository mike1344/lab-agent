import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# 操作说明链接只允许 http(s) 外链或以 / 开头的站内路径，避免 javascript: 等危险协议被渲染成可点击链接。
USAGE_DOC_URL_PATTERN = re.compile(r"^(https?://|/)", re.IGNORECASE)


def _normalize_usage_doc_url(value: str | None) -> str | None:
    """去空格；空字符串视为清空；其余必须符合协议白名单。"""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > 500:
        raise ValueError("操作说明链接过长（最多 500 字符）")
    if not USAGE_DOC_URL_PATTERN.match(cleaned):
        raise ValueError("操作说明仅支持 http(s) 链接或以 / 开头的站内路径")
    return cleaned


class EquipmentBase(BaseModel):
    lab_id: int
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=50)
    quantity: int = Field(default=1, ge=0, le=10000)
    description: str | None = None
    usage_doc_url: str | None = None
    status: int = Field(default=1, ge=0, le=1)

    @field_validator("name", "code")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned

    @field_validator("usage_doc_url")
    @classmethod
    def normalize_usage_doc_url(cls, value: str | None) -> str | None:
        return _normalize_usage_doc_url(value)


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    lab_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=100)
    code: str | None = Field(default=None, min_length=2, max_length=50)
    quantity: int | None = Field(default=None, ge=0, le=10000)
    description: str | None = None
    usage_doc_url: str | None = None
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

    @field_validator("usage_doc_url")
    @classmethod
    def normalize_usage_doc_url(cls, value: str | None) -> str | None:
        return _normalize_usage_doc_url(value)

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
