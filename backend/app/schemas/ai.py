from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    # 历史消息只接受用户和助手角色，避免客户端伪造 system/developer 指令。
    role: Literal["user", "assistant"]
    # 单条历史消息限长，防止请求体过大以及无意中消耗过多模型上下文。
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    # 当前问题允许容纳完整预约描述，但仍设置合理上限。
    message: str = Field(min_length=1, max_length=2000)
    # 仅保留少量历史消息，防止一次请求携带无限上下文。
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
