from pydantic import BaseModel, Field, field_validator


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    # 回复某条顶级评论时携带；为空表示发表顶级评论
    parent_id: int | None = None

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("评论内容不能为空")
        return cleaned
