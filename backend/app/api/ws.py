"""WebSocket 实时通知端点。

鉴权：浏览器端 WebSocket 无法自定义 Authorization 请求头，JWT 改走 ?token= 查询参数。
校验链与 get_current_user 完全一致：签名 → 用户存在 → 未禁用 → 密码版本指纹一致，
改密后旧 token 同样连不上 WS。

心跳：客户端每 25 秒发 "ping"，服务端回 "pong"。一来让服务端 receive 感知断连，
二来刷新 nginx 等中间层的读超时（默认 60s），空闲连接不会被中途掐断。
"""

import hmac

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import SessionLocal
from app.models.user import User
from app.services.ws import manager
from app.utils.jwt import build_password_version, decode_access_token

router = APIRouter(tags=["WebSocket 实时通知"])

# 自定义关闭码取 4000+ 应用私有区间：4401 = 鉴权失败。前端收到后不再自动重连。
WS_CLOSE_UNAUTHORIZED = 4401


def _authenticate_token(token: str) -> int | None:
    """校验 JWT，返回 user_id；任何一步失败返回 None。"""
    try:
        payload = decode_access_token(token)
    except Exception:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None
        if not hmac.compare_digest(
            payload.get("password_version", ""),
            build_password_version(user.password),
        ):
            return None
    return int(user_id)


@router.websocket("/ws/notifications")
async def notifications_endpoint(websocket: WebSocket, token: str = ""):
    user_id = _authenticate_token(token)
    # 先 accept 再按需 close，才能把自定义关闭码（4401）送达客户端；
    # 未 accept 直接 close 只会变成握手失败，前端拿不到关闭码。
    await websocket.accept()
    if user_id is None:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return

    manager.connect(user_id, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass  # 客户端关闭页面/网络断开：正常退出
    finally:
        manager.disconnect(user_id, websocket)
