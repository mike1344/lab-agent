from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReservationCreate(BaseModel):
    lab_id: int
    reservation_date: date
    start_time: time
    end_time: time
    purpose: str = Field(min_length=2, max_length=1000)
    repeat_weeks: int = Field(default=1, ge=1, le=4, description="重复周数，1=只约一次，最多4周")

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self


class ReservationReview(BaseModel):
    status: str
    review_comment: str | None = Field(default=None, max_length=500)


class ReservationUpdate(BaseModel):
    reservation_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    purpose: str | None = Field(default=None, min_length=2, max_length=1000)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self


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
