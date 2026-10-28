# ============================================================
# 后端镜像：FastAPI + Uvicorn（含 AI 依赖）
# 构建思路：先复制依赖清单安装依赖（利用 Docker 层缓存），再复制代码。
# ============================================================

# Python 版本可用 --build-arg PYTHON_VERSION=3.14 调整。
# 默认 3.12：Linux 下各依赖的预编译 wheel 覆盖最完整，构建最不容易踩坑。
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# TZ + tzdata：预约系统对时间敏感，容器统一东八区；
# curl 供容器健康检查使用（docker-compose.yml 中的 healthcheck）。
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依赖安装。requirements.txt 是当前可运行环境的完整锁定版本（含 AI 依赖）；
# 国内机器默认走清华镜像加速，海外服务器可加
# --build-arg PIP_INDEX=https://pypi.org/simple 换回官方源。
ARG PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
COPY requirements.txt ./
RUN pip install --no-cache-dir -i ${PIP_INDEX} -r requirements.txt

# 复制应用代码。.dockerignore 已排除 .venv、uploads、chroma_db、.env 等。
COPY . .

EXPOSE 8000

# 启动流程：
#   1. alembic upgrade head —— 幂等执行数据库迁移（新库自动建全部表，老库自动升级结构）；
#   2. Uvicorn 启动，--proxy-headers 让日志记录到 Nginx 转发过来的真实访问 IP；
#   3. WEB_CONCURRENCY 为进程数，可在 .env 中调整（AI 流式长连接，默认 2）。
CMD ["sh", "-c", "alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips '*'"]
