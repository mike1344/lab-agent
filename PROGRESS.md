# 项目进度记录

更新时间：2026-09-23

## 当前结论

课程第 08～27 节对应的主要代码已经完成并保存在当前工作区。核心前后端业务链已通过自动化测试和浏览器端到端验收，前端生产构建成功，ChromaDB 与 LangGraph 均已在本机实际运行。当前仅有“使用用户自己的 OpenAI API Key 调用真实模型”未执行；不配置 Key 时，本地 AI 模式仍可完整运行。

## 课程任务完成情况

| 节次 | 任务 | 状态 | 对应实现 |
| --- | --- | --- | --- |
| 08 | Vue 封装 axios 并联调 | 已完成 | `fronted/src/utils/request.js`、`fronted/src/api/` |
| 09 | 用户注册 | 已完成并测试 | `/api/auth/register`、`register.vue` |
| 10 | 后端文件上传 API | 已完成并测试 | `/api/upload/image`、静态 `/uploads` |
| 11 | 修改个人信息 | 已完成并测试 | `/api/user/profile`、个人中心 |
| 12 | 修改密码 | 已完成 | `/api/user/password` |
| 13 | 用户列表 | 已完成 | 管理员分页、模糊查询 |
| 14 | 用户增删改 | 已完成 | 管理员新增、编辑、删除、禁用、角色管理 |
| 15 | 实验室管理 | 已完成并测试 | 实验室增删改查与开放状态 |
| 16 | 实验室设备管理 | 已完成并测试 | 设备增删改查、实验室筛选 |
| 17 | 学生端实验室和设备列表 | 已完成 | 根据角色自动切换列表与管理界面 |
| 18 | 实验室预约 | 已完成并测试 | 日期/时间/用途、时间冲突校验 |
| 19 | 我的预约和预约审核 | 已完成并测试 | 学生取消、管理员通过/拒绝 |
| 20 | AI 助手后端 | 已完成 | `/api/ai/chat/stream` |
| 21 | AI 助手前端与联调 | 已完成 | `chat.vue`、POST SSE 解析 |
| 22 | RAG 知识库 | 已完成并实际运行 | Markdown 知识库、ChromaDB、本地离线向量；失败时自动降级关键词检索 |
| 23 | Tool Calling 查询数据 | 已完成 | 十类工具：查询实验室/设备/公告、检索文档、创建/查询/取消预约、推荐实验室等 |
| 24 | LangGraph 预约 Agent | 已安装并测试 | 循环图 `retrieve → agent ⇄ tools`，`GRAPH_ENGINE` 为 `LangGraph循环工具` |
| 25 | SSE 流式输出与过程可见 | 已完成并测试 | status/tool_start/tool_end/tool/token/done 事件 |
| 26 | 首页与课程收尾 | 已完成 | 角色化统计、预约流程、README、测试 |
| 27 | 项目图解 | 已完成 | `ARCHITECTURE.md`：系统全景、代码映射、登录/预约时序、AI 流程图 |

## 已验证结果

- `npm run build`：通过。
- `python -m unittest discover -s tests -v`：通过，6 个测试。
- 后端 Python 编译与导入：通过。
- 自动化测试覆盖：注册、重复注册、错误登录、JWT 改密失效、管理员越权、实验室、设备、预约冲突、审核、取消、真假图片上传、AI SSE、多轮 AI 预约、否定/撤回预约和最新参数选择。
- 测试数据：SQLite 数据库、ChromaDB 索引和上传文件均放在独立临时目录，测试结束自动清理，没有修改开发 MySQL 数据。
- LangGraph：已安装，运行时确认 `GRAPH_ENGINE = "LangGraph循环工具"`（`retrieve → agent ⇄ tools` 循环图）。
- ChromaDB：已安装，运行时确认 `retrieval = "ChromaDB"`；采用本地哈希向量，无需下载嵌入模型。
- RAG 索引同步：Markdown 新增/修改会增量 upsert，删除会清理旧向量；临时目录隔离测试通过。
- 依赖健康检查：`pip check` 通过，无损坏或冲突依赖。
- OpenAI 兼容实现：Chat Completions 的 Function Calling（`tools` + `tool_choice`）与流式输出（`stream=True` 的 `delta.content`），兼容第三方 OpenAI 格式 API。
- 浏览器端到端验收：登录、角色首页、实验室、设备、学生预约、管理员审核、学生回看、个人中心、用户管理、AI SSE 均通过。
- 前端浏览器控制台：验收期间无 error/warning。

## 本轮质量强化

- REST 预约和 AI 预约共用 `services/reservation.py`，避免两套规则漂移。
- MySQL 创建预约时锁定实验室行，降低并发请求造成重复预约的风险。
- AI 支持“上一轮提供参数、本轮确认预约”，服务端每轮最多执行一次写工具。
- SSE 前端改为真正逐 token 响应式更新，并修复停止生成的控制器竞态。
- 业务异常、参数异常和服务器异常使用真实 HTTP 4xx/5xx，同时保留统一响应体。
- JWT 绑定密码版本指纹，修改密码后旧 Token 自动失效。
- 上传接口同时校验 MIME 与 PNG/JPEG/WEBP 文件特征，不再接受伪装图片。
- ChromaDB 根据 Markdown 内容哈希自动同步，不会长期返回过期知识。
- 实验室、设备和管理员新增用户会拒绝空白名称；更新接口会拒绝把数据库必填字段设为 `null`。
- AI 不会把“不要帮我预约”识别为确认；连续修改预约参数后，以最近一次完整参数为准。撤回或讨论其他问题后，旧参数不能再被一句“确认预约”重新启用。
- 取消和审核会锁定同一条预约记录；审核通过前还会复核日期与实验室开放状态。
- 当天的预约开始时间必须晚于当前时间，避免提交后立刻成为无法履行的待审核记录。

## 当前环境与未完成项

1. 未提供 OpenAI API Key，因此没有发起真实模型请求或消耗额度；未配置 Key 时 AI 页面使用本地可运行模式。
2. 浏览器验收使用的临时账号、实验室、设备和预约已经按精确标识清理；开发 MySQL 中原有账号 `aaa` 未改动。
3. 本轮检查时后端 `http://127.0.0.1:8000/docs` 与前端 `http://127.0.0.1:5173` 都返回 HTTP 200；如服务停止，可按下方命令重新启动。

## 下次继续入口

```powershell
# 1. 安装全部依赖（换电脑或重建虚拟环境时执行）
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-all.txt

# 2. 回归后端
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# 3. 启动后端
.\.venv\Scripts\uvicorn.exe app.main:app --reload

# 4. 新终端启动前端
cd ..\fronted
npm run dev
```

## 重要文件

- 项目运行与结构说明：`README.md`
- 项目架构与流程图解：`ARCHITECTURE.md`
- 后端入口：`backend/app/main.py`
- 后端路由汇总：`backend/app/api/__init__.py`
- AI Agent：`backend/app/ai/agent.py`
- AI 工具：`backend/app/ai/tools.py`
- 预约业务服务：`backend/app/services/reservation.py`
- 前端路由：`fronted/src/router/index.js`
- axios 封装：`fronted/src/utils/request.js`
- 自动化测试：`backend/tests/test_api.py`
