import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.ai.agent import GRAPH_ENGINE, build_prompt_context, run_graph, run_model_tools, stream_answer
from app.database import SessionLocal
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatRequest

router = APIRouter(prefix="/ai", tags=["AI 实验室助手"])
logger = logging.getLogger("lab_agent.ai")


def sse_event(event: str, data: dict) -> str:
    """SSE 每条消息以空行结束，data 使用 JSON 便于前端稳定解析。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
def chat_stream(data: ChatRequest, current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    history = [item.model_dump() for item in data.history]

    def generate_events():
        db = SessionLocal()
        try:
            yield sse_event("status", {"message": f"正在通过 {GRAPH_ENGINE} 分析问题…"})
            state = run_graph(data.message, user_id, db, history)
            yield sse_event("status", {"message": f"已使用 {state.get('retrieval_engine', '知识库')} 完成 RAG 检索"})

            # 模型工具调用：逐个发 tool_start/tool_end 事件
            model_tool_results = []
            for event in run_model_tools(data.message, user_id, db, history):
                if event["type"] == "tool_start":
                    yield sse_event("tool_start", {"label": event["label"]})
                elif event["type"] == "tool_end":
                    yield sse_event("tool_end", {"label": event["label"]})
                elif event["type"] == "done":
                    model_tool_results = event["results"]

            used_tools = state.get("used_tools", [])
            if model_tool_results:
                used_tools.append("AI Tool Calling")
            if used_tools:
                yield sse_event("tool", {"message": "已调用：" + "、".join(used_tools)})

            context = build_prompt_context(state, model_tool_results)
            for token in stream_answer(data.message, history, context):
                yield sse_event("token", {"content": token})
            yield sse_event("done", {"message": "回答完成"})
        except Exception:
            logger.exception("AI 助手处理失败")
            yield sse_event("error", {"message": "AI 助手暂时无法回答，请稍后重试"})
        finally:
            db.close()

    return StreamingResponse(generate_events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
