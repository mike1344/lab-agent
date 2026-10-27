from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.permission import get_current_admin
from app.models.agent_tool_log import AgentToolLog
from app.models.operation_log import OperationLog
from app.models.user import User
from app.schemas.operation_log import OperationLogResponse
from app.services.export import build_excel_response

router = APIRouter(prefix="/operation-logs", tags=["操作日志"])


@router.get("/tool-calls")
def list_agent_tool_calls(
    limit: int = Query(default=50, ge=1, le=200),
    tool_name: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员查看 AI 写工具调用审计（创建/取消预约的入参、结果、耗时、幂等键）。"""
    query = db.query(AgentToolLog)
    if tool_name.strip():
        query = query.filter(AgentToolLog.tool_name == tool_name.strip())
    items = query.order_by(AgentToolLog.id.desc()).limit(limit).all()
    return Response.success(
        data=[
            {
                "id": item.id,
                "user_id": item.user_id,
                "tool_name": item.tool_name,
                "arguments": item.arguments,
                "result": item.result,
                "success": item.success,
                "duration_ms": item.duration_ms,
                "idempotency_key": item.idempotency_key,
                "note": item.note,
                "create_time": item.create_time,
            }
            for item in items
        ]
    )


@router.get("")
def get_operation_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    username: str = "",
    method: str = "",
    success: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """管理员分页查询操作日志：支持按操作人、请求方法与结果过滤。"""
    query = db.query(OperationLog)
    if username.strip():
        query = query.filter(OperationLog.username.like(f"%{username.strip()}%"))
    if method.strip():
        query = query.filter(OperationLog.method == method.strip().upper())
    if success is not None:
        query = query.filter(OperationLog.success == success)

    total = query.count()
    logs = query.order_by(OperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Response.success(
        data={
            "list": [OperationLogResponse.model_validate(log) for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/export")
def export_operation_logs(
    username: str = "",
    start_date: str = "",
    end_date: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员导出审计报告（按操作人/时间范围），供合规检查与事后追溯。"""
    query = db.query(OperationLog)
    if username.strip():
        query = query.filter(OperationLog.username.like(f"%{username.strip()}%"))
    if start_date:
        query = query.filter(OperationLog.create_time >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(OperationLog.create_time < datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
    items = query.order_by(OperationLog.id.asc()).all()
    rows = [
        [
            item.id,
            item.username,
            item.user_id or "",
            "管理员" if item.is_superuser else "用户",
            item.method,
            item.path,
            item.summary,
            "成功" if item.success else "失败",
            item.http_status,
            item.message,
            item.ip or "",
            item.duration_ms,
            str(item.create_time),
        ]
        for item in items
    ]
    return build_excel_response(
        sheet_title="操作审计",
        headers=[
            "ID",
            "操作人",
            "用户ID",
            "角色",
            "方法",
            "接口",
            "操作说明",
            "结果",
            "状态码",
            "结果信息",
            "IP",
            "耗时(ms)",
            "时间",
        ],
        rows=rows,
        filename_prefix="操作审计",
    )
