from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api import api
from app.api.upload import UPLOAD_DIR
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.config import settings
from app.database import Base, engine
from app.middleware.operation_log import operation_log_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.request_id import configure_logging, request_id_middleware
from app.models import (  # noqa: F401 - 注册 ORM 模型
    AgentToolLog,
    Announcement,
    AnnouncementComment,
    AnnouncementRead,
    BlackoutPeriod,
    Course,
    CourseEnrollment,
    Equipment,
    Favorite,
    Lab,
    LoginLog,
    Notification,
    OperationLog,
    Procurement,
    Repair,
    Reservation,
    User,
)
from app.services.observability import init_sentry, setup_metrics
from app.services.schedule import (
    _run_in_fresh_session,
    expire_stale_reservations,
    remind_upcoming_reservations,
    start_scheduler,
)

# 结构化日志：统一格式并带 request_id（必须在任何模块打日志之前配置）
configure_logging(settings.LOG_LEVEL)

# 开发便捷：启动时创建缺失的表（不会修改已有表结构）。
# 生产环境可在 .env 设置 AUTO_CREATE_TABLES=false，表结构统一交给 Alembic 迁移管理。
if settings.AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期：启动时拉起定时任务，关闭时优雅停止。

    过期关闭/开课提醒在启动瞬间会先同步执行一轮，开发时改完数据刷新页面即可看到效果，
    不需要等 5 分钟的调度间隔。
    """
    scheduler = None
    if settings.SCHEDULER_ENABLED:
        scheduler = start_scheduler()
        # 启动瞬间先同步执行一轮，开发时改完数据刷新页面即可看到效果，不用等 5 分钟间隔。
        _run_in_fresh_session("expire_stale_reservations", expire_stale_reservations)
        _run_in_fresh_session("remind_upcoming_reservations", remind_upcoming_reservations)
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

# 错误监控（SENTRY_DSN 为空时跳过）与 Prometheus 指标（/metrics）
init_sentry()
setup_metrics(app)

# 上传目录通过 /uploads 暴露，前端可直接预览上传后的图片。
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 配置跨域请求：允许的前端来源从 .env 的 CORS_ORIGINS 读取（多个用英文逗号分隔），
# 部署时修改配置即可，不需要改代码。
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

# 操作日志审计：记录所有写操作。先注册 → CORS 后注册成为更外层中间件，
# 跨域预检（OPTIONS）不会进入审计逻辑，普通写请求的日志也不会被 CORS 拦截影响。
app.middleware("http")(operation_log_middleware)
# 限流在审计外层：被限流的请求不会产生审计日志噪音
app.middleware("http")(rate_limit_middleware)
# request_id 在限流外层：429 响应也会带上 X-Request-ID
app.middleware("http")(request_id_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的前端源，不要直接写 ["*"]
    allow_credentials=True,  # ✅ 关键：允许前端携带 Authorization token
    allow_methods=["*"],  # 允许所有请求方法 GET POST PUT DELETE OPTIONS
    allow_headers=["*"],  # 允许所有请求头（包含Authorization）
)
# 注册汇总后的 API 路由
app.include_router(api)

app.add_exception_handler(
    BusinessException,
    business_exception_handler,
)

app.add_exception_handler(
    StarletteHTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    Exception,
    global_exception_handler,
)


@app.get("/")
def root():
    return {"message": "FastAPI工程正在运行中"}


@app.get("/health")
def health():
    """存活探针：只证明进程活着，监控系统或负载均衡可定期请求。"""
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    """就绪探针：数据库可达才返回 200，否则 503，供负载均衡摘除异常实例。"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - 探针失败只返回 503，不抛异常栈
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    return {"status": "ready", "database": "ok"}
