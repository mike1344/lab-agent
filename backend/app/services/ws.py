"""WebSocket 连接管理与实时通知推送。

要点：
1. 连接按 user_id 分组，同一用户多端在线（开两个标签页）各自独立收消息；
2. 推送可能来自线程池里的同步接口或 APScheduler 线程，而 send 是协程——
   通过连接建立时记录的事件循环 run_coroutine_threadsafe 投递，fire-and-forget
   不阻塞调用方，也不可能在事件循环内自我死锁；
3. 推送是“尽力而为”：用户不在线就跳过，落库的通知记录由前端轮询兜底。
   多 worker 部署时连接分散在不同进程，本管理器只能推到自己进程持有的连接，
   其余用户靠轮询——这是不引入 Redis 的取舍，见 TODO.md。
"""

import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger("lab_agent.ws")


class ConnectionManager:
    """user_id -> {(websocket, 该连接所在事件循环)} 的连接注册表。"""

    def __init__(self):
        self._connections: dict[int, set[tuple[WebSocket, asyncio.AbstractEventLoop]]] = {}

    def connect(self, user_id: int, websocket: WebSocket) -> None:
        loop = asyncio.get_running_loop()
        self._connections.setdefault(user_id, set()).add((websocket, loop))

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        remaining = self._connections.get(user_id)
        if not remaining:
            return
        remaining = {(ws, loop) for ws, loop in remaining if ws is not websocket}
        if remaining:
            self._connections[user_id] = remaining
        else:
            self._connections.pop(user_id, None)

    def push_to_user(self, user_id: int, payload: dict) -> int:
        """把消息投递给该用户的所有在线连接；可在任意线程调用。

        返回成功调度发送的连接数（不保证客户端确实收到）。
        """
        text = json.dumps(payload, ensure_ascii=False, default=str)
        delivered = 0
        for websocket, loop in list(self._connections.get(user_id, ())):
            try:
                asyncio.run_coroutine_threadsafe(websocket.send_text(text), loop)
                delivered += 1
            except RuntimeError:
                # 事件循环已关闭（应用停机中），顺手清掉死连接。
                self.disconnect(user_id, websocket)
            except Exception:  # noqa: BLE001 - 推送失败绝不能影响业务主流程
                logger.exception("WebSocket 推送失败 user_id=%s", user_id)
        return delivered

    def is_online(self, user_id: int) -> bool:
        return bool(self._connections.get(user_id))

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


manager = ConnectionManager()


def push_notification(*, user_id: int, type: str, title: str, content: str, related_id: int | None = None) -> None:
    """向在线用户实时推送一条站内通知（字段与 /api/notifications/mine 的条目一致）。"""
    manager.push_to_user(
        user_id,
        {
            "kind": "notification",
            "notification": {
                "type": type,
                "title": title,
                "content": content,
                "related_id": related_id,
            },
        },
    )
