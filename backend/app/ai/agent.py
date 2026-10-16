import json
import re
from typing import Any, TypedDict

from openai import OpenAI
from sqlalchemy.orm import Session

from app.ai.knowledge import search_documents
from app.ai.tools import (
    TOOL_SCHEMAS,
    cancel_reservation,
    check_lab_availability,
    create_lab_reservation,
    get_latest_announcements,
    get_my_reservations,
    get_today,
    list_lab_equipments,
    list_open_labs,
    recommend_lab,
)
from app.config import settings


class AgentState(TypedDict, total=False):
    """LangGraph 节点之间传递的状态。"""

    message: str
    history: list[dict[str, str]]
    user_id: int
    db: Session
    retrieved_docs: list[dict[str, str]]
    retrieval_engine: str
    tool_context: list[str]
    used_tools: list[str]
    messages: list[dict[str, Any]]
    final_answer: str


def retrieve_node(state: AgentState) -> AgentState:
    documents, engine = search_documents(state["message"])
    return {"retrieved_docs": documents, "retrieval_engine": engine}


def has_explicit_reservation_intent(message: str) -> bool:
    normalized_message = "".join(message.lower().split())
    # 明确确认
    if re.fullmatch(
        r"(?:请|麻烦)?(?:确认|确认预约|帮我预约|立即预约|提交预约|创建预约|就这个|选这个|就选这个|可以|行|好的)[。.!！]*",
        normalized_message,
    ):
        return True
    # 直接说选哪个实验室
    if re.search(r"(选|就|要).{0,4}(实验室|id|编号|\d+号)", normalized_message):
        return True
    # 预约开头
    return bool(
        re.match(
            r"^(?:请|麻烦)?(?:帮我|立即|提交|创建)?预约(?:实验室|id|编号|\d)",
            normalized_message,
            re.IGNORECASE,
        )
    )


def has_cancel_reservation_intent(message: str) -> bool:
    normalized_message = "".join(message.lower().split())
    if normalized_message in {"取消", "撤销", "不要", "算了", "先不"}:
        return True
    return bool(
        re.match(r"^(?:我|请|麻烦)?(?:现在|先)?(?:不要|别|不想|不需要|不用|无需|暂不|先不|取消|撤销)", normalized_message)
        and re.search(r"预约|创建|提交|确认", normalized_message)
    )


def get_user_messages(state: AgentState) -> list[str]:
    user_messages = [
        item["content"]
        for item in state.get("history", [])
        if item.get("role") == "user" and item.get("content")
    ]
    return [*user_messages[-10:], state["message"]]


def local_tool_node(state: AgentState) -> AgentState:
    """没有模型 Key 时用明确规则选择只读工具。"""
    message = state["message"]
    context = []
    used_tools = ["search_lab_docs"]
    if any(word in message for word in ("实验室", "开放", "设备", "机房")):
        context.append(list_open_labs(state["db"]))
        used_tools.append("list_open_labs")

    pattern = r"预约.*?(?:ID\s*)?(\d+).*?(\d{4}-\d{2}-\d{2}).*?(\d{1,2}:\d{2})\s*[-到至]\s*(\d{1,2}:\d{2}).*?用途[：:]\s*([^\r\n]+)"
    matched = None
    for user_message in reversed(get_user_messages(state)[-2:]):
        if has_cancel_reservation_intent(user_message):
            break
        matched = re.search(pattern, user_message, re.IGNORECASE)
        if matched:
            break
    if matched and not settings.OPENAI_API_KEY and has_explicit_reservation_intent(message):
        arguments = {
            "lab_id": int(matched.group(1)),
            "reservation_date": matched.group(2),
            "start_time": matched.group(3),
            "end_time": matched.group(4),
            "purpose": matched.group(5),
        }
        context.append(create_lab_reservation(state["db"], state["user_id"], arguments))
        used_tools.append("create_lab_reservation")
    elif not settings.OPENAI_API_KEY and has_cancel_reservation_intent(message):
        context.append("已停止本次预约意向，没有创建预约。")
    elif matched and not settings.OPENAI_API_KEY:
        context.append("预约信息已识别；请回复确认预约后再创建预约。")
    return {"tool_context": context, "used_tools": used_tools}


# ========== LangGraph 图内循环工具调用 ==========

SYSTEM_PROMPT = (
    "你是智能实验室预约助手。严格遵守：\n"
    "1. 绝对不要问用户'你是谁'、'你的姓名'、'学号'——系统已经告诉你了\n"
    "2. 绝对不要问用户要时间段、人数——这些调 recommend_lab 工具自动查\n"
    "3. 用户说想做实验/要预约时，必须先调 get_today 和 recommend_lab 工具，不许自己瞎编实验室和时间\n"
    "4. recommend_lab 返回的每个选项包含：实验室ID、名称、可约时间段、设备\n"
    "5. 把选项列给用户选（比如'1号实验室14:00-16:00，2号实验室15:00-17:00'）\n"
    "6. 用户说'选1号'、'就这个'、'确认'后，直接调 create_lab_reservation，把 lab_id、日期、开始结束时间填好\n"
    "7. purpose 用途根据用户说的内容自动填，不要问用户\n"
    "8. 创建成功后告诉用户预约编号和状态即可"
)


def _execute_tool(name: str, arguments: dict, db: Session, user_id: int, message: str) -> str:
    """执行单个工具，返回结果字符串。"""
    if name == "list_open_labs":
        return list_open_labs(db)
    if name == "search_lab_docs":
        documents, _ = search_documents(arguments.get("query", message))
        return "\n".join(item["text"] for item in documents)
    if name == "get_my_reservations":
        return get_my_reservations(db, user_id, arguments.get("status"))
    if name == "cancel_reservation":
        return cancel_reservation(db, user_id, int(arguments["reservation_id"]))
    if name == "check_lab_availability":
        return check_lab_availability(db, int(arguments["lab_id"]), arguments["reservation_date"])
    if name == "get_latest_announcements":
        return get_latest_announcements(db)
    if name == "recommend_lab":
        return recommend_lab(db, arguments["reservation_date"], arguments.get("period", "afternoon"), int(arguments.get("duration_hours", 2)))
    if name == "get_today":
        return get_today()
    if name == "list_lab_equipments":
        return list_lab_equipments(db)
    if name == "create_lab_reservation":
        if not has_explicit_reservation_intent(message):
            return "预约参数已识别，请用户明确回复确认预约后再创建。"
        return create_lab_reservation(db, user_id, arguments)
    return f"未知工具：{name}"


def agent_node(state: AgentState) -> AgentState:
    """图里的 agent 节点：调大模型，拿到回复（可能含 tool_calls）。

    没有配置模型 Key 时退化为本地规则节点（查开放实验室、识别预约格式），
    保证离线模式也能走完同一张图。
    """
    if not settings.OPENAI_API_KEY:
        return local_tool_node(state)

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    messages = state.get("messages") or [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(state.get("history") or [])[-10:],
        {"role": "user", "content": state["message"]},
    ]

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )
    assistant_msg = response.choices[0].message

    if assistant_msg.tool_calls:
        # 有工具要调，把 assistant 消息加进 messages，等 tools_node 执行
        new_messages = messages + [assistant_msg.model_dump()]
        return {"messages": new_messages}
    else:
        # 没有工具要调，就是最终回答
        return {"final_answer": assistant_msg.content or "", "messages": messages}


def execute_tools_node(state: AgentState) -> AgentState:
    """执行 messages 里最后一条 assistant 消息的 tool_calls，结果加回 messages。"""
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    messages = state["messages"]
    last_assistant = messages[-1]

    tool_results = []
    for tc in last_assistant.get("tool_calls", []):
        name = tc["function"]["name"]
        args = json.loads(tc["function"]["arguments"] or "{}")
        result = _execute_tool(name, args, state["db"], state["user_id"], state["message"])
        tool_results.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": result,
        })

    new_messages = messages + tool_results
    return {"messages": new_messages}


def should_continue(state: AgentState) -> str:
    """条件边：最后一条消息有 tool_calls 就继续执行工具，否则结束。"""
    if not settings.OPENAI_API_KEY:
        return "end"
    messages = state.get("messages") or []
    if not messages:
        return "end"
    last = messages[-1]
    if last.get("role") == "assistant" and last.get("tool_calls"):
        return "tools"
    return "end"


def build_graph():
    """构建 Agent 循环图：agent → 有 tool_calls → tools（执行工具）→ 回到 agent；没有 tool_calls → END"""
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(AgentState)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", execute_tools_node)

        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "agent")

        # agent 后条件判断：有工具就去 tools，没有就 END
        graph.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", "end": END},
        )
        # tools 执行完回到 agent
        graph.add_edge("tools", "agent")

        return graph.compile(), "LangGraph循环工具"
    except ImportError:
        return None, "顺序编排（安装 langgraph 后自动启用）"


AGENT_GRAPH, GRAPH_ENGINE = build_graph()


def run_graph(
    message: str,
    user_id: int,
    db: Session,
    history: list[dict[str, str]] | None = None,
) -> AgentState:
    initial_state: AgentState = {
        "message": message,
        "history": history or [],
        "user_id": user_id,
        "db": db,
    }
    if AGENT_GRAPH:
        return AGENT_GRAPH.invoke(initial_state)
    state = {**initial_state, **retrieve_node(initial_state)}
    return {**state, **local_tool_node(state)}


def run_model_tools(
    message: str,
    user_id: int,
    db: Session,
    history: list[dict[str, str]] | None = None,
):
    """真实模型通过 Chat Completions Tool Calling 自主选择工具，yield 每个工具的开始/结束事件。

    yield 的是 dict：{"type": "tool_start", "name": ...} / {"type": "tool_end", "name": ..., "result": ...}
    最后 yield {"type": "done", "results": [...]} 带上所有结果。
    """
    if not settings.OPENAI_API_KEY:
        yield {"type": "done", "results": []}
        return
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    # 从数据库查当前用户信息，直接告诉 AI，不用问用户
    from app.models.user import User
    current_user = db.query(User).filter(User.id == user_id).first()
    user_info = f"当前登录用户：{current_user.full_name or current_user.username}（ID:{current_user.id}）" if current_user else f"用户ID:{user_id}"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\n\n【当前用户信息】{user_info}，预约时自动用这个申请人，不要问用户姓名学号。"},
        *(history or [])[-10:],
        {"role": "user", "content": message},
    ]
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )
    tool_calls = response.choices[0].message.tool_calls or []
    tool_results = []
    write_tool_handled = False
    for tool_call in tool_calls:
        name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments or "{}")
        tool_label = {
            "get_today": "换算今天/明天日期",
            "list_open_labs": "查询开放实验室",
            "list_lab_equipments": "查询设备列表",
            "search_lab_docs": "检索知识库",
            "check_lab_availability": "查询实验室占用情况",
            "recommend_lab": "智能推荐实验室",
            "get_my_reservations": "查询我的预约",
            "cancel_reservation": "取消预约",
            "get_latest_announcements": "查询最新公告",
            "create_lab_reservation": "创建预约",
        }.get(name, name)
        yield {"type": "tool_start", "name": name, "label": tool_label}
        if name == "create_lab_reservation" and write_tool_handled:
            result = "本轮已经处理过一次预约请求，没有重复创建。"
        else:
            result = _execute_tool(name, arguments, db, user_id, message)
            if name == "create_lab_reservation":
                write_tool_handled = True
        tool_results.append(result)
        yield {"type": "tool_end", "name": name, "label": tool_label, "result": result}
    yield {"type": "done", "results": tool_results}


def build_prompt_context(state: AgentState, model_tool_results: list[str]) -> str:
    document_text = "\n\n".join(
        f"来源：{item.get('source', 'knowledge')}\n{item['text']}" for item in state.get("retrieved_docs", [])
    )
    tool_text = "\n".join(state.get("tool_context", []) + model_tool_results)
    return f"知识库内容：\n{document_text}\n\n系统实时数据/工具结果：\n{tool_text or '无'}"


def stream_answer(message: str, history: list[dict[str, str]], context: str):
    """有 Key 时流式输出回答。"""
    if not settings.OPENAI_API_KEY:
        answer = (
            "我已根据本地知识库和系统实时数据完成查询。\n\n"
            f"{context}\n\n"
            "如需由 AI 直接创建预约，请按 预约实验室ID 1 2026-10-01 09:00-11:00 用途：实验教学 的格式告诉我。"
        )
        for index in range(0, len(answer), 12):
            yield answer[index : index + 12]
        return

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": (
            "你是实验室信息查询助手。根据知识库和工具结果准确、简洁地回答用户问题，"
            "不要编造实验室、设备或预约状态。只回答用户提出的问题。"
        )},
        *history[-10:],
        {"role": "user", "content": f"用户问题：{message}\n\n{context}"},
    ]
    stream = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
