# 部署手册（Docker Compose 一键包）

用 Docker Compose 一条命令拉起整套系统：MySQL 数据库 + FastAPI 后端 + Nginx/Vue 前端。
适用：Linux 云服务器（推荐）、Windows/macOS 装 Docker Desktop、支持 Docker 的 NAS。

## 1. 部署架构

```text
浏览器
  │  http://服务器IP:80（默认，可在 .env 里改 WEB_PORT）
  ▼
frontend 容器（Nginx）
  ├─ /            → 前端静态文件（Vue 构建产物，history 路由已处理）
  ├─ /api/*       → backend 容器（Uvicorn :8000，SSE 流式已关闭缓冲）
  ├─ /uploads/*   → backend 容器（用户上传的图片）
  └─ /health      → backend 容器（探活接口）
                        │
                        ▼
                  mysql 容器（:3306，仅在容器网络内可达，不暴露公网）
```

数据用三个数据卷持久化（`docker compose down` 不会丢；`docker compose down -v` 才会清空）：

| 数据卷 | 内容 |
| --- | --- |
| `lab_agent_mysql_data` | MySQL 全部数据 |
| `lab_agent_uploads_data` | 用户上传的图片 |
| `lab_agent_chroma_data` | AI 知识库向量索引（删了也不要紧，首次查询会自动重建） |

## 2. 首次部署（五步）

### 2.1 安装 Docker

Linux 服务器（已安装可跳过）：

```bash
curl -fsSL https://get.docker.com | sh
```

Windows / macOS：安装 Docker Desktop（Windows 需要开启 WSL2 后端）。

### 2.2 拉取代码

```bash
git clone https://github.com/mike1344/lab-agent.git
cd lab-agent
```

### 2.3 配置参数

```bash
cp .env.docker.example .env
```

编辑 `.env`，至少修改这三项：

- `MYSQL_ROOT_PASSWORD`、`MYSQL_PASSWORD` —— 数据库密码；
- `JWT_SECRET_KEY` —— 登录凭证签名密钥（生成命令写在 .env 注释里）。

> 不创建 `.env` 也能启动，但会使用内置弱口令，仅适合本机跑通演示。

### 2.4 启动

```bash
docker compose up -d --build
```

- 首次要构建镜像并下载依赖（视网络情况 5～20 分钟），之后的每次启动只要几秒。
- 启动顺序自动编排：MySQL 就绪 → 后端执行数据库迁移（自动建表）并启动 → 前端可访问。
- 看到启动完成后，浏览器打开 `http://服务器IP/`（本机试用则是 `http://localhost/`）。

### 2.5 创建第一个管理员（首次必须）

```bash
docker compose exec backend python -m scripts.create_admin --username admin --email admin@example.com
```

按提示输入密码（输入时不显示是正常现象）。

**验证：** 打开 `http://服务器IP/health` 返回 `{"status":"ok"}` 即部署成功；然后用管理员账号登录系统。

## 3. 上线公共服务器前必做

1. **改掉 `.env` 里的数据库密码和 JWT 密钥**（见 2.3）。
2. **只放行必要端口**：云服务器安全组/防火墙放行 `WEB_PORT`（默认 80）和 SSH；
   数据库 3306 与后端 8000 不要对公网开放（本方案默认就没有暴露它们）。
3. （可选）**配置 HTTPS**：用云厂商 SSL 证书、certbot 或宝塔/1Panel，把 443 反代到本机 `WEB_PORT`。

## 4. 日常运维

### 查看状态和日志

```bash
docker compose ps                      # 三个容器是否都在运行
docker compose logs -f backend         # 后端日志（Ctrl+C 退出跟踪）
docker compose logs -f frontend        # Nginx 日志
docker compose logs -f mysql           # 数据库日志
```

### 停止 / 启动 / 重启

```bash
docker compose stop                    # 停止全部容器（数据保留）
docker compose start                   # 再次启动
docker compose restart backend         # 只重启后端
```

### 更新到最新代码

```bash
git pull
docker compose up -d --build
```

后端启动时会自动执行 `alembic upgrade head`，数据库结构有变化会自动升级；
前端镜像重新构建后即包含新页面。

### 备份

（在服务器 SSH 终端执行）

```bash
# ① 数据库：导出到当前目录
docker compose exec mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" lab_agent' > backup-db-$(date +%F).sql

# ② 上传图片：把数据卷打包
docker run --rm -v lab_agent_uploads_data:/data -v "$PWD":/backup alpine tar czf /backup/backup-uploads-$(date +%F).tgz -C /data .

# ③ 向量索引不必备份：删掉后首次查询会自动重建
```

### 恢复

```bash
# 数据库：恢复到（全新的）lab_agent 库
docker compose exec -T mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" lab_agent' < backup-db-2026-01-01.sql

# 上传图片：解包回数据卷
docker run --rm -v lab_agent_uploads_data:/data -v "$PWD":/backup alpine sh -c 'cd /data && tar xzf /backup/backup-uploads-2026-01-01.tgz'
```

## 5. 常见问题排查

| 现象 | 处理办法 |
| --- | --- |
| 页面打不开 / 502 | 看后端是否就绪：`docker compose logs backend --tail 100` |
| 改过数据库密码后连不上 | MySQL 密码只在数据卷首次初始化时写入；要么改回旧密码，要么 `docker compose down -v` 清空重来（**数据会全部丢失**，慎用） |
| 端口 80 被占用 | `.env` 里把 `WEB_PORT` 改成 8080 等，再 `docker compose up -d` |
| AI 回答不是逐字出现 | 默认 nginx 已关闭缓冲；若你改过 `fronted/nginx.conf`，确认 `proxy_buffering off` 还在 |
| 上传大图报 413 | 上传接口本身限 5MB；nginx 已放宽到 10MB。改过配置需同步 |
| 时间显示不对 | 容器已统一东八区；再查宿主机 `date`（宿主机时间错，容器也会错） |
| 构建很慢或失败 | 国内网络已默认清华 pip 源 + npmmirror npm 源；海外服务器可把两个 Dockerfile 里的 `PIP_INDEX` / `NPM_REGISTRY` 改回官方源 |
| 想临时看接口文档 | 默认不对外反代 /docs；可 `docker compose exec backend curl -s http://127.0.0.1:8000/openapi.json`，或自行在 `fronted/nginx.conf` 加 location 转发 |
| 日志出现 ChromaDB telemetry 相关提示 | 已通过 `ANONYMIZED_TELEMETRY=False` 关闭匿名上报；偶发残留提示可忽略 |

## 6. 本套件文件清单

| 文件 | 作用 |
| --- | --- |
| `docker-compose.yml` | 编排入口：定义 mysql / backend / frontend 三个容器与数据卷 |
| `.env.docker.example` | 部署参数模板（复制为根目录 `.env` 使用） |
| `backend/Dockerfile` | 后端镜像：装依赖 → 复制代码 → 启动时先执行迁移再跑 Uvicorn |
| `backend/.dockerignore` | 构建后端镜像时排除的文件（虚拟环境、上传目录、密钥等） |
| `fronted/Dockerfile` | 前端镜像：两阶段构建（Node 编译 → Nginx 托管） |
| `fronted/nginx.conf` | Nginx 站点配置：history 路由回退、/api 与 /uploads 反代、SSE 流式特调 |
| `fronted/.dockerignore` | 构建前端镜像时排除的文件（node_modules、dist 等） |

## 附：不使用 Docker 的手动部署要点

- 后端：安装 Python 3.12+ 与 MySQL 8，`pip install -r requirements-all.txt`；参照 `backend/.env.example`
  配置（生产环境设 `AUTO_CREATE_TABLES=false`）；执行 `alembic upgrade head` 后以 Uvicorn 启动，
  用 systemd 守护进程。
- 前端：`npm run build` 后把 `fronted/dist` 交给 Nginx，站点配置照抄 `fronted/nginx.conf` 的三件事：
  `try_files ... /index.html` 回退、`/api` 反代并关闭缓冲、`/uploads` 反代。
- 本项目的 Docker 方案就是把以上步骤固化成了镜像，逻辑一一对应。
