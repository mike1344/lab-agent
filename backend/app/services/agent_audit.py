"""AI 工具调用审计与幂等。

- 写工具（创建/取消预约）在执行前按「用户 + 工具 + 参数」计算幂等键；
  已成功执行的同一请求直接返回历史结果，避免模型重试造成重复写操作。
- 每次写工具调用（含等待用户确认、失败）都落一条审计记录；
- 幂等键有数据库唯一约束兜底，并发下也不会重复写入两条成功记录。
"""

import hashlib
import json
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent_tool_log import AgentToolLog

logger = logging.getLogger("lab_agent.agent_audit")

WRITE_TOOLS = {"create_lab_reservation", "cancel_reservation"}


def build_idempotency_key(user_id: int, tool_name: str, arguments: dict) -> str:
    """写操作幂等键：同一用户、同一工具、同一参数得到同一摘要。"""
    payload = json.dumps(
        {"user_id": user_id, "tool": tool_name, "arguments": arguments},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def find_successful_call(db: Session, idempotency_key: str) -> AgentToolLog | None:
    return (
        db.query(AgentToolLog)
        .filter(AgentToolLog.idempotency_key == idempotency_key, AgentToolLog.success.is_(True))
        .first()
    )


def record_tool_call(
    db: Session,
    *,
    user_id: int,
    tool_name: str,
    arguments: dict,
    result: str,
    success: bool,
    duration_ms: int,
    idempotency_key: str | None = None,
    note: str = "",
) -> AgentToolLog | None:
    """落审计记录；幂等键冲突（并发重复）时回滚并返回 None，不影响主流程。"""
    row = AgentToolLog(
        user_id=user_id,
        tool_name=tool_name,
        arguments=json.dumps(arguments, ensure_ascii=False, default=str),
        result=result[:4000],
        success=success,
        duration_ms=duration_ms,
        idempotency_key=idempotency_key,
        note=note,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        logger.info("幂等键冲突，跳过重复审计记录：%s", (idempotency_key or "")[:12])
        return None
    except Exception:  # noqa: BLE001 - 审计失败不能影响主流程
        db.rollback()
        logger.exception("工具审计写入失败")
        return None
