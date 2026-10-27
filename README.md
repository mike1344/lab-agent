# 智能实验室预约系统

这是一个 Vue 3 + Element Plus + FastAPI + SQLAlchemy + MySQL 的前后端分离项目，覆盖用户、实验室、设备、预约和 AI 助手等主要业务链。

项目模块关系、预约时序和 AI 处理流程见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)。

## 已实现功能

- axios 统一封装、JWT 自动携带、统一错误提示、路由守卫
- 用户注册、登录、个人资料修改、密码修改、图片上传
- 管理员用户增删改查、角色和账号状态管理
- 实验室与设备增删改查，学生端列表展示
- 实验室预约、时间冲突校验、我的预约、取消预约、管理员审核
- 实验室周/日视图预约日历（占用总览、点空档直接预约）
- 首页角色化统计 + ECharts 可视化（预约趋势、实验室使用排行、报修状态分布）
- 定时任务：过期预约自动关闭、开课前站内提醒（APScheduler，可在 .env 关闭）
- 通知实时推送：WebSocket 在线即达（审核结果、报修进度、预约提醒），掉线自动回到 30 秒轮询兜底
- 登录安全：图形验证码（一次性消费，可在 .env 关闭）、连续失败锁定、登录日志审计查询
- 操作日志审计：中间件自动记录所有写操作（操作人、接口、结果、IP、耗时），管理员可筛选查询
- 设备操作说明：设备可绑定操作手册链接，详情弹窗内嵌预览（支持站内 PDF 与新窗口打开）
- 公告互动：评论与一层回复、已读标记（列表未读提示）、管理员已读回执统计
- 收藏：实验室/设备星标收藏，「只看收藏」快速筛选
- 采购管理：申请 → 到货 → 验收状态机，验收自动入库（库存 +数量），已验收记录留痕不可删
- 实验课程：教师建课（周几+时段+学期区间）、选课名单管理，课表与自由预约双向冲突校验
- 多维导出：预约、设备台账、报修记录、用户列表四个 Excel 导出（统一封装、中文文件名不乱码）
- 邮件通知：审核结果/开课提醒/报修进度同步发邮件（SMTP 未配置时自动降级为仅站内通知）
- 认证增强：短效 access + 长效 refresh token，401 自动无感续期后重放请求
- 可观测性：结构化日志（request_id 链路追踪）、Prometheus `/metrics`、Sentry（配 DSN 生效）、`/ready` 就绪探针
- 接口限流：认证/AI/普通接口分级限流（内存固定窗口，超限 429）
- 工程化：GitHub Actions CI（ruff 门禁 + 后端测试 + 前端构建 + 镜像构建）、dev/staging/prod 三套配置模板
- 合规与安全：审计日志留存 180 天并支持导出、危险操作密码二次确认（电子签名）、上传文件可选 ClamAV 扫描
- 报表与运维：机时/费用报表（按实验室+按用户，双工作表导出）、`scripts/backup.sh` 每日备份脚本与恢复演练流程
- AI 助手：本地知识库、ChromaDB RAG、工具调用、LangGraph 编排、SSE 流式输出
- 独立 SQLite 自动化测试，不污染开发 MySQL 数据

## 目录结构

```text
lab_agent/
├─ backend/
│  ├─ app/
│  │  ├─ ai/              # RAG、工具与 LangGraph Agent
│  │  ├─ api/             # FastAPI 路由
│  │  ├─ common/          # 统一响应与异常处理
│  │  ├─ dependencies/    # JWT 与管理员权限依赖
│  │  ├─ knowledge/       # AI 助手 Markdown 知识库
│  │  ├─ models/          # SQLAlchemy 数据模型
│  │  ├─ schemas/         # Pydantic 请求/响应模型
│  │  └─ utils/           # 密码和 JWT 工具
│  ├─ scripts/            # 管理脚本
│  └─ tests/              # 接口回归测试
├─ fronted/
│  └─ src/
│     ├─ api/             # 按业务模块封装请求
│     ├─ layouts/         # 登录后的主框架
│     ├─ router/          # 页面路由与登录守卫
│     ├─ utils/           # axios、token 和用户状态
│     └─ views/           # 各业务页面
├─ docker-compose.yml     # Docker 一键部署入口（MySQL + 后端 + 前端）
└─ DEPLOY.md              # 部署手册（架构、备份恢复、排障）
```

## 启动后端

1. 在 MySQL 中创建 `lab_agent` 数据库。
2. 将 `backend/.env.example` 复制为 `backend/.env` 并修改数据库密码和 JWT 密钥。
3. 安装依赖并启动：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-all.txt
uvicorn app.main:app --reload
```

首次使用的新数据库需要创建管理员：

```powershell
python -m scripts.create_admin --username admin --email admin@example.com
```

后端启动后可访问 `http://127.0.0.1:8000/docs` 查看并调试全部接口；`/health` 为服务探活接口（返回 `{"status": "ok"}`），部署后供监控系统使用。

### 数据库表结构变更（Alembic）

表结构统一由 Alembic 迁移管理（启动时的自动建表只负责"创建缺失的表"，不会修改已有表）：

```powershell
cd backend
.\.venv\Scripts\alembic.exe upgrade head      # 全新数据库：执行迁移建全部表
.\.venv\Scripts\alembic.exe stamp head        # 老库（表已由 create_all 建好）：只登记版本号，不动表数据
.\.venv\Scripts\alembic.exe revision --autogenerate -m "变更说明"   # 改完 app/models 后：生成迁移并检查生成文件
.\.venv\Scripts\alembic.exe upgrade head      # 再执行迁移完成升级
```

生产环境可在 `.env` 设置 `AUTO_CREATE_TABLES=false`，完全交给迁移管理。

> **容易混淆的一点：** ApiPost 是“接口调试客户端”，不是后端服务器。
> 必须先让上面的 `uvicorn` 命令保持运行，ApiPost 才能向 FastAPI 发送请求。

### 在 ApiPost 中调试接口

1. 新建环境变量 `baseUrl`，值设为 `http://127.0.0.1:8000`。
2. 先请求 `POST {{baseUrl}}/api/auth/login`，Body 选择 JSON：

```json
{
  "username": "你的用户名",
  "password": "你的密码"
}
```

3. 从返回数据的 `data.token` 复制 JWT；调试需要登录的接口时，在请求头加入：

```text
Authorization: Bearer 复制到的token
```

4. 如果 ApiPost 提示连接失败，先在浏览器打开 `http://127.0.0.1:8000/docs`：
   能打开说明后端已经启动；打不开则回到后端终端查看报错。

## 启动前端

```powershell
cd fronted
npm install
npm run dev
```

前端默认访问 `http://127.0.0.1:8000`。如果后端地址不同，请修改 `fronted/.env.development`。

## Docker 一键部署（服务器 / 生产环境）

一台装好 Docker 的机器上，三条命令拉起整套系统（MySQL + 后端 + 前端 + Nginx）：

```bash
cp .env.docker.example .env     # 修改里面的数据库密码与 JWT 密钥
docker compose up -d --build    # 首次构建视网络情况需 5～20 分钟
docker compose exec backend python -m scripts.create_admin --username admin --email admin@example.com
```

完成后浏览器打开 `http://服务器IP/`（本机试用为 `http://localhost/`）。
架构说明、备份恢复、更新升级与排障手册见 [`DEPLOY.md`](./DEPLOY.md)。

## AI 助手配置

不填写 `OPENAI_API_KEY` 时，AI 页面仍可使用本地知识库、查询开放实验室，并按固定格式创建预约。填写 Key 后会启用 OpenAI 兼容接口（Chat Completions）的模型工具选择与流式回答。

本地模式预约示例：

```text
预约实验室ID 1 2026-10-01 09:00-11:00 用途：实验教学
```

也可以分两轮对话：第一轮发送上面的完整参数，紧接着第二轮回复 `确认预约`。如果修改过预约参数，以最新一轮完整参数为准；如果说过“取消预约”或转去讨论其他问题，需要重新提供完整参数。后端只读取用户消息，并在当前轮检测到明确确认后才允许执行写入工具；同一轮最多执行一次创建操作。

知识库内容位于 `backend/app/knowledge/`，新增 Markdown 文件后会在首次查询时写入 ChromaDB。

项目使用本地“字符 + 相邻双字符”哈希向量写入 ChromaDB，因此首次查询不需要再从网络下载嵌入模型。这个实现轻量、便于离线运行；正式项目可把 `build_local_embedding()` 替换成 OpenAI Embeddings 或其他中文向量模型。

## 验证项目

一条命令完成「安装依赖 → ruff 门禁 → 后端回归测试 → 前端单测与构建」：

```powershell
# Windows（仓库根目录）
pwsh -File scripts\verify.ps1
```

```bash
# Linux / macOS
./scripts/verify.sh
```

常用参数：`-SkipInstall`（依赖已装好，只跑检查）、`-SkipFrontend`（只验后端；Linux 用 `--skip-frontend`）。

依赖说明：

- `backend/requirements.txt`：**当前可运行环境的完整锁定版本**（含 openai / chromadb / langgraph），新环境安装以它为准；
- `backend/requirements-all.txt`：项目直接依赖的宽松版本（便于升级），Docker 镜像与 CI 之外的手动安装可用；
- 后端测试使用独立 SQLite 与临时 ChromaDB，不连接开发 MySQL；前端单测使用 Node 内置 `node --test`（`fronted/tests/`），覆盖下载文件名解析与登录凭证存储工具。

预约日期可以选择今天或未来，但当天的开始时间必须晚于服务器当前时间。管理员审核时也会重新检查预约时间和实验室开放状态。

## 推荐的代码阅读顺序

1. `fronted/src/utils/request.js`：理解 axios 如何统一添加 JWT 和处理错误。
2. `fronted/src/api/`：理解页面如何按业务模块调用后端。
3. `backend/app/main.py` 与 `backend/app/api/`：理解 FastAPI 路由和依赖注入。
4. `backend/app/models/`、`backend/app/schemas/`：区分数据库模型与接口数据校验。
5. `backend/app/ai/knowledge.py`、`tools.py`、`agent.py`：依次理解 RAG、工具调用和 LangGraph 编排。
