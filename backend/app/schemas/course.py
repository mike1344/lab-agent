from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CourseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    lab_id: int
    weekday: int = Field(ge=1, le=7)
    start_time: time
    end_time: time
    start_date: date
    end_date: date
    description: str | None = None
    # 仅管理员可指定授课教师；教师身份调用时强制为本人
    teacher_id: int | None = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        if self.end_date < self.start_date:
            raise ValueError("学期结束日期不能早于开始日期")
        return self


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    lab_id: int | None = None
    weekday: int | None = Field(default=None, ge=1, le=7)
    start_time: time | None = None
    end_time: time | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_pairs(self):
        # 只校验同时提交的字段对，部分更新时由落库前的最终值兜底校验
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("学期结束日期不能早于开始日期")
        return self


class EnrollmentCreate(BaseModel):
    student_ids: list[int] = Field(min_length=1, max_length=200)


class EnrollmentResponse(BaseModel):
    student_id: int
    username: str
    full_name: str | None = None
    email: str
    enrolled: bool = True

    model_config = ConfigDict(from_attributes=True)
