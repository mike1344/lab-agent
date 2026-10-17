from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.config import settings
from app.database import Base, engine
from app.models import Announcement, BlackoutPeriod, Equipment, Lab, Notification, Repair, Reservation, User  # noqa: F401 - 注册 ORM 模型
from app.api.upload import UPLOAD_DIR

# 开发便捷：启动时创建缺失的表（不会修改已有表结构）。
# 生产环境可在 .env 设置 AUTO_CREATE_TABLES=false，表结构统一交给 Alembic 迁移管理。
if settings.AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)

app = FastAPI()

# 上传目录通过 /uploads 暴露，前端可直接预览上传后的图片。
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 配置跨域请求：允许的前端来源从 .env 的 CORS_ORIGINS 读取（多个用英文逗号分隔），
# 部署时修改配置即可，不需要改代码。
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

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
    """部署探活接口：监控系统或负载均衡可定期请求它确认服务存活。"""
    return {"status": "ok"}
