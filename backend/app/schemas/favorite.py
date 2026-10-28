from typing import Literal

from pydantic import BaseModel


class FavoriteCreate(BaseModel):
    """收藏请求：类型只允许实验室或设备，防止写入无效目标。"""

    target_type: Literal["lab", "equipment"]
    target_id: int
