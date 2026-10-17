# 智能实验室预约系统

这是一个 Vue 3 + Element Plus + FastAPI + SQLAlchemy + MySQL 的前后端分离项目，覆盖用户、实验室、设备、预约和 AI 助手等主要业务链。

项目模块关系、预约时序和 AI 处理流程见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)。

## 已实现功能

- axios 统一封装、JWT 自动携带、统一错误提示、路由守卫
- 用户注册、登录、个人资料修改、密码修改、图片上传
- 管理员用户增删改查、角色和账号状态管理
- 实验室与设备增删改查，学生端列表展示
- 实验室预约、时间冲突校验、我的预约、取消预约、管理员审核
- 首页角色化统计
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
└─ fronted/
   └─ src/
      ├─ api/             # 按业务模块封装请求
      ├─ layouts/         # 登录后的主框架
      ├─ router/          # 页面路由与登录守卫
      ├─ utils/           # axios、token 和用户状态
      └─ views/           # 各业务页面
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

```powershell
cd fronted
npm run build

cd ..\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试会覆盖注册登录、管理员权限、改密后旧 JWT 失效、实验室、设备、预约冲突、审核、取消、图片内容校验、AI SSE、多轮 AI 预约和 ChromaDB 索引同步。SQLite 数据库、ChromaDB 索引及测试上传文件均位于临时目录，不会连接开发 MySQL。

预约日期可以选择今天或未来，但当天的开始时间必须晚于服务器当前时间。管理员审核时也会重新检查预约时间和实验室开放状态。

## 推荐的代码阅读顺序

1. `fronted/src/utils/request.js`：理解 axios 如何统一添加 JWT 和处理错误。
2. `fronted/src/api/`：理解页面如何按业务模块调用后端。
3. `backend/app/main.py` 与 `backend/app/api/`：理解 FastAPI 路由和依赖注入。
4. `backend/app/models/`、`backend/app/schemas/`：区分数据库模型与接口数据校验。
5. `backend/app/ai/knowledge.py`、`tools.py`、`agent.py`：依次理解 RAG、工具调用和 LangGraph 编排。
