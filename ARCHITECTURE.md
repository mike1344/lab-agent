# 智能实验室预约系统：项目图解

建议先从“系统全景”理解模块边界，再沿着预约和 AI 两条主流程阅读代码。

## 1. 系统全景

```mermaid
flowchart LR
    U[学生 / 管理员] --> V[Vue 3 页面]
    V --> A[axios 请求封装]
    A -->|HTTP + JWT| F[FastAPI 路由]
    F --> D[权限与数据库依赖]
    D --> S[业务 Service / ORM]
    S --> M[(MySQL)]

    V -->|POST + SSE| AI[AI 对话接口]
    AI --> G[LangGraph]
    G --> R[ChromaDB RAG]
    G --> T[Tool Calling]
    R --> K[Markdown 知识库]
    T --> M
    AI -. 配置 API Key 后 .-> O[OpenAI 兼容 API（Chat Completions）]
```

阅读提示：

- Vue 只负责交互与展示，不能代替后端鉴权。
- axios 统一添加 JWT；FastAPI 的依赖再次验证用户和管理员权限。
- 普通业务数据存放在 MySQL；知识文档及向量索引由 Markdown 与 ChromaDB 管理。
- 没有 OpenAI API Key 时，LangGraph、RAG、工具查询和 SSE 仍可在本地运行。

## 2. 前后端代码映射

```mermaid
flowchart TB
    subgraph Frontend[fronted/src]
        FV[views 页面]
        FA[api 业务请求]
        FR[router 路由守卫]
        FU[utils/request.js]
        FL[layouts 主框架]
        FV --> FA --> FU
        FR --> FL --> FV
    end

    subgraph Backend[backend/app]
        BM[main.py]
        BA[api 路由]
        BD[dependencies 权限]
        BS[schemas 参数校验]
        BO[models ORM]
        BC[common 统一响应/异常]
        BI[ai Agent/RAG/Tools]
        BM --> BA
        BA --> BD
        BA --> BS
        BA --> BO
        BA --> BC
        BA --> BI
    end

    FU -->|/api/*| BA
```

## 3. 登录与鉴权流程

```mermaid
sequenceDiagram
    actor User as 用户
    participant Page as Vue 登录页
    participant Axios as axios 封装
    participant API as FastAPI
    participant DB as MySQL

    User->>Page: 输入用户名和密码
    Page->>Axios: login(data)
    Axios->>API: POST /api/auth/login
    API->>DB: 查询用户并校验密码哈希
    DB-->>API: 用户记录
    API-->>Axios: JWT + 用户信息
    Axios-->>Page: 保存 Token 和用户缓存
    Page->>Page: 跳转系统首页

    Note over Axios,API: 后续请求自动携带 Authorization: Bearer JWT
    Axios->>API: 访问受保护接口
    API->>API: get_current_user / get_current_admin
    API-->>Axios: 业务数据或 401/403
```

## 4. 实验室预约主流程

```mermaid
sequenceDiagram
    actor Student as 学生
    participant Web as Vue
    participant API as FastAPI
    participant DB as MySQL
    actor Admin as 管理员

    Student->>Web: 选择实验室、日期和时间
    Web->>API: POST /api/reservations
    API->>DB: 检查实验室开放状态
    API->>DB: 检查 pending/approved 时间重叠
    alt 时间冲突
        API-->>Web: 400 该时间段已有预约
    else 可以预约
        API->>DB: 写入 pending 预约
        API-->>Web: 提交成功
    end

    Admin->>Web: 打开预约审核
    Web->>API: PUT /api/reservations/{id}/review
    API->>DB: 更新 approved 或 rejected
    API-->>Web: 审核完成
    Student->>Web: 查看我的预约和审核意见
```

时间冲突的核心判断是：`已有开始时间 < 新结束时间` 且 `已有结束时间 > 新开始时间`。这比只比较开始时间更完整，也能正确识别“包含”和“部分重叠”。

## 5. AI 助手处理流程

```mermaid
flowchart TD
    Q[用户问题] --> SSE[POST /api/ai/chat/stream]
    SSE --> G[LangGraph 状态图]
    G --> R[retrieve 节点]
    R --> C[ChromaDB 向量检索]
    C -->|异常时| W[本地关键词检索]
    C --> X[知识上下文]
    W --> X
    X --> A[agent 节点]
    A -->|无 Key| L[local_tool_node 本地规则]
    A -->|有 Key| M[Chat Completions 工具调用]
    M -->|有 tool_calls| T[execute_tools_node 执行工具]
    T --> A
    A --> B[组合回答上下文]
    L --> B
    B --> K{是否配置 OpenAI API Key}
    K -->|否| LOCAL[本地答案分片]
    K -->|是| MODEL[模型流式回答]
    LOCAL --> E[status / tool_start / tool_end / tool / token / done]
    MODEL --> E
    E --> UI[Vue 实时展示过程和答案]
```

这里有三层“可继续替换”的设计：

1. `build_local_embedding()` 可替换为正式中文 Embedding 模型。
2. `ai/tools.py` 的工具（共十个）可继续扩展；图内 `execute_tools_node` 与图外 `run_model_tools()` 都统一经 `_execute_tool` 分发。
3. `stream_answer()` 已把本地回答与真实模型回答统一成流式迭代器，前端不需要区分实现。

## 6. 功能模块与代码入口

| 功能模块 | 前端入口 | 后端入口 |
| --- | --- | --- |
| 登录与鉴权（JWT、axios 封装、路由守卫） | `utils/request.js`、`utils/auth.js`、`router/index.js`、`views/login.vue`、`views/register.vue` | `api/auth.py`、`dependencies/auth.py`、`dependencies/permission.py`、`utils/jwt.py`、`utils/password.py` |
| 用户与个人中心（资料、密码、头像上传、管理员用户管理） | `views/user.vue` | `api/user.py`、`api/upload.py` |
| 实验室、设备与不可约时段 | `views/lab.vue`、`views/equ.vue` | `api/lab.py`、`api/equipment.py`、`api/blackout.py` |
| 预约与审核 | `views/reservation.vue` | `api/reservation.py`、`services/reservation.py` |
| 公告、报修与通知 | `views/announcement.vue`、`views/repair.vue`、`layouts/layouts.vue` | `api/announcement.py`、`api/repair.py`、`api/notification.py` |
| AI 助手（RAG、Tool Calling、LangGraph、SSE） | `views/chat.vue` | `api/ai.py`、`ai/knowledge.py`、`ai/tools.py`、`ai/agent.py` |
| 首页统计 | `views/home.vue` | `api/stats.py` |

