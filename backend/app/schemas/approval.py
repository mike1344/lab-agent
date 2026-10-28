from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ApprovalStepInput(BaseModel):
    """单个审批节点的录入结构：按角色或按指定人员。"""

    name: str | None = Field(default=None, max_length=100)
    approver_type: Literal["role", "user"] = "role"
    approver_role: Literal["admin", "teacher"] | None = None
    approver_id: int | None = None

    @model_validator(mode="after")
    def validate_approver(self):
        if self.approver_type == "role":
            if self.approver_role is None:
                raise ValueError("按角色审批时必须选择管理员或教师")
            if self.approver_id is not None:
                raise ValueError("按角色审批时不能同时指定人员")
        else:
            if self.approver_id is None:
                raise ValueError("指定人员审批时必须选择审批人")
            if self.approver_role is not None:
                raise ValueError("指定人员审批时不能同时选择角色")
        if self.name is not None:
            self.name = self.name.strip() or None
        return self


class ApprovalFlowUpsert(BaseModel):
    """管理员为某个实验室配置审批流（整体覆盖节点）。"""

    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool = True
    steps: list[ApprovalStepInput] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def normalize(self):
        self.name = self.name.strip()
        if self.description is not None:
            self.description = self.description.strip() or None
        return self
