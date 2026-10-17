import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.ai.agent import GRAPH_ENGINE, build_prompt_context, run_graph_stream, stream_answer
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
        try:
            yield sse_event("status", {"message": f"正在通过 {GRAPH_ENGINE} 分析问题…"})
            final_state: dict = {}
            model_tool_results: list[str] = []
            tools_line_sent = False

            # 工具事件与回答 token 全部来自图内实时透传，端点只做转发；
            # 不再另起一条模型调用路径，避免工具被重复执行、模型被重复调用。
            for event in run_graph_stream(data.message, user_id, history):
                event_type = event["type"]
                if event_type == "status":
                    yield sse_event("status", {"message": event["message"]})
                elif event_type == "tool_start":
                    yield sse_event("tool_start", {"label": event["label"]})
                elif event_type == "tool_end":
                    yield sse_event("tool_end", {"label": event["label"]})
                    model_tool_results.append(event["result"])
                elif event_type == "token":
                    # 回答开始前先补发“已调用”汇总，保持和旧版一致的展示顺序。
                    if not tools_line_sent and model_tool_results:
                        yield sse_event("tool", {"message": "已调用：AI Tool Calling"})
                        tools_line_sent = True
                    yield sse_event("token", {"content": event["content"]})
                elif event_type == "graph_done":
                    final_state = event["state"]

            used_tools = list(final_state.get("used_tools", []))
            if model_tool_results:
                used_tools.append("AI Tool Calling")
            if used_tools and not tools_line_sent:
                yield sse_event("tool", {"message": "已调用：" + "、".join(used_tools)})

            if not final_state.get("answer_streamed"):
                # 本地模式（无 Key）或图内没有产出回答时的兜底流式输出。
                context = build_prompt_context(final_state, model_tool_results)
                for token in stream_answer(data.message, history, context):
                    yield sse_event("token", {"content": token})
            yield sse_event("done", {"message": "回答完成"})
        except Exception:
            logger.exception("AI 助手处理失败")
            yield sse_event("error", {"message": "AI 助手暂时无法回答，请稍后重试"})

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
