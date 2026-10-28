from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OperationLogResponse(BaseModel):
    # from_attributes：允许直接从 SQLAlchemy ORM 对象构造（model_validate）
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    user_id: int | None = None
    is_superuser: bool
    method: str
    path: str
    summary: str
    success: bool
    http_status: int
    message: str
    ip: str | None = None
    duration_ms: int
    create_time: datetime
