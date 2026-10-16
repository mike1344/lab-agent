from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=10000)
    is_pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = Field(default=None, min_length=2, max_length=10000)
    is_pinned: bool | None = None


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    is_pinned: bool
    publisher_id: int
    publisher_name: str
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)
