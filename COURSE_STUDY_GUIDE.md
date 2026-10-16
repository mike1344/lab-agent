# 智能实验室预约系统：第 00–27 节学习导航与速查

下面这份是方便回顾的**速查目录**。如果你正在第一次学习，先打开 [知识点与项目代码同步学习版](docs/course/LEARN_WITH_CODE.md)：它把每个知识点、对应的项目代码、代码解析和复现检查放在同一处，不需要在“讲解文档”和“代码文档”之间来回跳。

四份分册和合并版适合需要查看大段完整源文件时使用。**本页的“关键代码”只是速查节选；首次学习以同步学习版为主，需要完整上下文时再打开分册或源码。**

| 课程节次 | 详细复现教程 | 学习主线 |
| --- | --- | --- |
| 00–27 首选 | [知识点与项目代码同步学习版](docs/course/LEARN_WITH_CODE.md) | 每讲一个知识点，立即看对应代码和逐句解析 |
| 00–08 | [环境、Vue、FastAPI、登录、JWT、axios](docs/course/00-08-foundation.md) | 理解项目骨架及一次前后端请求 |
| 09–14 | [注册、上传、个人资料、密码、用户管理](docs/course/09-14-users.md) | 实现用户生命周期与权限 |
| 15–19 | [实验室、设备、学生列表、预约与审核](docs/course/15-19-business.md) | 实现完整预约业务链 |
| 20–27 | [AI、RAG、Tool Calling、LangGraph、SSE 与图解](docs/course/20-27-ai.md) | 理解 AI 对话的真实执行顺序 |
| 00–27 合一 | [完整对照版（四份合并，一个文件）](docs/course/full-reference.md) | 顺序通读或全文搜索 |

学完每节课后，如果想遮住代码只检查自己是否理解概念，再看 [复习笔记](docs/course/review-notes.md)。

详细版使用当前工作区中的代码复现课程功能；本页保留逐节的快速提示和源码入口。前 00–07 节是根据课程标题和现有项目反推的学习路线；第 08–27 节对应已经实现的功能。它不是课程视频逐字稿，因此讲课顺序、界面截图与现在的代码可能略有差异。

> 仓库里的前端目录确实叫 `fronted`（不是常见的 `frontend`），以下路径沿用现有命名。示例中的密钥、密码只用占位文字，真实值只应写进本机的 `backend/.env`，不要放进前端或提交到仓库。

## 开始前：怎样使用这份手册

1. 先看本节的“知识点”，再打开“源码入口”并搜索文中提到的函数名。
2. 手敲或调试“关键代码”，不要只复制结果；本页的关键代码是**速查节选**，省略了与本节无关的上下文。想看某个知识点在项目里的**完整实现**，请打开对应节的详细教程（完整源码，不省略）。
3. 完成本节“动手检查”，再继续下一节。需要了解全局模块关系时，配合 [项目图解](ARCHITECTURE.md) 阅读。
4. 遇到接口问题时，先打开 `http://127.0.0.1:8000/docs`。ApiPost 是接口客户端，不是后端服务器。

本项目的主链路是：`Vue 页面 → src/api → axios → FastAPI 路由 → Pydantic/鉴权 → Service/ORM → MySQL`。AI 链路另外包含 `LangGraph → RAG/工具 → 本地回答或模型 → SSE → Vue`。

常用启动与验证命令（已创建数据库并配置好 `backend/.env` 的前提下）：

```powershell
# 终端 A：启动 FastAPI
cd 'F:\fastapi项目实战\lab_agent\backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# 终端 B：启动 Vue
cd 'F:\fastapi项目实战\lab_agent\fronted'
npm run dev

# 学完一组课程后的回归检查
npm run build
cd ..\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 第 00 节：课程大纲与完整项目认识

- **知识点**：把功能拆为四层：前端交互、后端接口、数据库业务、AI 助手。弄清“页面显示数据”和“服务器实际授权”是两件事。
- **源码入口**：[后端入口](backend/app/main.py)、[路由汇总](backend/app/api/__init__.py)、[前端路由](fronted/src/router/index.js)、[整体架构](ARCHITECTURE.md)。
- **关键代码**：后端从一个总路由把不同业务模块接入应用，前端则把不同页面挂到路由中：

  ```python
  # backend/app/main.py：所有 /api/... 请求由汇总路由转发
  app.include_router(api)
  ```

- **动手检查**：画出“学生提交预约 → 管理员审核 → 学生查看结果”的流程，标出每一步属于前端、后端还是数据库。对照 [预约时序图](ARCHITECTURE.md) 校正。

## 第 01 节：搭建环境，创建前端 Vue 工程

- **知识点**：Node/npm 管理前端依赖；Python 虚拟环境管理后端依赖；Vite 是开发服务器和打包工具。`backend/.env` 配后端数据库/JWT，`fronted/.env.development` 配前端 API 地址，两者用途不同。
- **源码入口**：[前端依赖与脚本](fronted/package.json)、[Vite 配置](fronted/vite.config.js)、[后端依赖](backend/requirements-all.txt)、[配置读取](backend/app/config.py)。
- **关键代码**：`package.json` 的 `scripts` 把常用命令固定下来；运行 `npm run dev` 实际执行 Vite，`npm run build` 检查生产打包。后端用以下命令隔离依赖：

  ```powershell
  cd backend
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements-all.txt
  ```

- **动手检查**：启动前端并打开页面；再启动后端并打开 `/docs`。若 `/docs` 打不开，先看后端终端报错，不要在 ApiPost 中寻找“启动服务器”按钮。

## 第 02 节：搭建前端 Vue 主体框架

- **知识点**：`createApp` 挂载 Vue；Vue Router 根据 URL 显示页面；父路由配合 `<router-view>` 形成“固定导航 + 可切换内容”；Element Plus 提供表单、菜单等 UI 组件。
- **源码入口**：[Vue 入口](fronted/src/main.js)、[路由定义](fronted/src/router/index.js)、[主布局](fronted/src/layouts/layouts.vue)、[App 根组件](fronted/src/App.vue)。
- **关键代码**：`/` 对应主布局，`home` 等是它的子页面；登录和注册页放在布局外：

  ```js
  {
    path: '/',
    component: () => import('@/layouts/layouts.vue'),
    redirect: '/home',
    children: [{ path: 'home', component: () => import('@/views/home.vue') }]
  }
  ```

- **动手检查**：在浏览器切换“首页”“实验室”“设备”，观察地址栏与 `<router-view>` 内容变化；再解释为什么登录页不应显示后台侧边栏。

## 第 03 节：开发前端登录页面

- **知识点**：`reactive` 保存输入，`ref` 保存表单实例与加载状态；Element Plus `rules`/`validate()` 先做前端校验；真正的身份验证仍由后端完成。
- **源码入口**：[登录页面](fronted/src/views/login.vue)、[登录请求函数](fronted/src/api/auth.js)、[登录状态封装](fronted/src/utils/user.js)。
- **关键代码**：先校验再调用接口，`finally` 保证成功或失败都能取消按钮加载状态：

  ```js
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid || loadingValue.value) return
  loadingValue.value = true
  try {
    const res = await loginApi({ username: form.username.trim(), password: form.password })
    saveLoginData(res.data)
  } finally {
    loadingValue.value = false
  }
  ```

- **动手检查**：分别测试空用户名、错误密码、正确账号；在浏览器开发者工具 Network 中观察请求体和响应。密码不应写进 `localStorage`。

## 第 04 节：搭建后端 FastAPI 工程

- **知识点**：FastAPI `app` 是服务入口；`APIRouter` 按业务分组；`Depends(get_db)` 为每次请求提供数据库会话；CORS 允许指定前端源跨域请求。
- **源码入口**：[FastAPI 入口](backend/app/main.py)、[数据库会话](backend/app/database.py)、[路由汇总](backend/app/api/__init__.py)、[配置](backend/app/config.py)。
- **关键代码**：数据库会话使用 `yield/finally`，无论接口正常返回还是报错，最终都会关闭：

  ```python
  def get_db():
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```

- **动手检查**：打开 `/docs` 找到路由；解释 `Base.metadata.create_all(bind=engine)` 创建的是**表**而不是 MySQL 数据库本身，为什么仍需预先创建数据库。

## 第 05 节：开发后端登录 API 接口

- **知识点**：请求由 Pydantic 模型校验；SQLAlchemy 查询用户；数据库保存密码哈希，登录时用 `verify_password()` 比对，绝不能把明文密码直接比数据库字符串。
- **源码入口**：[登录接口](backend/app/api/auth.py)、[登录请求/响应模型](backend/app/schemas/auth.py)、[密码工具](backend/app/utils/password.py)、[用户模型](backend/app/models/user.py)。
- **关键代码**：错误凭证返回 401；账号存在但被禁用返回 403；验证通过后才签发 Token：

  ```python
  user = db.query(User).filter(User.username == data.username).first()
  if not user or not verify_password(data.password, user.password):
      raise BusinessException(code=BizCode.UNAUTHORIZED, message="账号或密码错误")
  if not user.is_active:
      raise BusinessException(code=BizCode.FORBIDDEN, message="账号被禁用")
  token = create_access_token(user.id, user.password)
  ```

- **动手检查**：用 `/docs` 或 ApiPost 分别请求不存在用户、错误密码、正确密码、禁用账号；比较 HTTP 状态码、响应体中的 `code` 和提示信息。

## 第 06 节：开发后端 JWT 用户认证

- **知识点**：JWT 是后端签名的登录凭证；请求头格式为 `Authorization: Bearer <token>`。Token 的签发、解析、过期校验与当前用户查询集中在后端；前端路由守卫只是用户体验，不能当成真正的权限控制。
- **源码入口**：[JWT 工具](backend/app/utils/jwt.py)、[当前用户依赖](backend/app/dependencies/auth.py)、[管理员依赖](backend/app/dependencies/permission.py)、[前端路由守卫](fronted/src/router/index.js)。
- **关键代码**：登录时写入用户 ID、过期时间和“密码版本”；改密后版本不匹配，旧 Token 自动失效：

  ```python
  payload = {
      "user_id": user_id,
      "password_version": build_password_version(password_hash),
      "exp": expire,
  }
  return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
  ```

- **动手检查**：登录后复制 Token 请求受保护接口；不带 Token、改坏 Token、修改密码后使用旧 Token，分别观察后端返回。不要把 JWT 密钥写进前端。

## 第 07 节：统一响应格式与全局异常处理

- **知识点**：成功/失败都用 `code/message/data` 结构，让前端容易统一处理；同时 HTTP 状态码应真实表示 400/401/403/500，不能所有错误都返回 HTTP 200。业务异常、参数校验异常和未知异常应分别处理。
- **源码入口**：[统一响应](backend/app/common/response.py)、[异常处理器](backend/app/common/exceptions.py)、[处理器注册](backend/app/main.py)。
- **关键代码**：业务错误先映射为 HTTP 状态码，再返回一致的 JSON 响应体：

  ```python
  http_status = code if 400 <= code <= 599 else int(BizCode.INTERNAL_ERROR)
  return JSONResponse(
      status_code=http_status,
      content=Response.error(code=exc.code, message=exc.message).model_dump(),
  )
  ```

- **动手检查**：故意向接口传错误类型或缺少必填字段，对比 400 校验错误和 401 未登录错误；解释为什么 500 的内部堆栈只应出现在后端日志中。

## 第 08 节：Vue 封装 axios 并实现前后端接口联调

- **知识点**：axios 实例统一设置 `baseURL` 和超时；请求拦截器自动加 JWT；响应拦截器集中处理业务错误、HTTP 错误、超时和 401 跳登录；页面只调用 `src/api` 的业务函数。
- **源码入口**：[axios 封装](fronted/src/utils/request.js)、[Token 存取](fronted/src/utils/auth.js)、[接口封装目录](fronted/src/api/auth.js)、[前端开发环境配置](fronted/.env.development)。
- **关键代码**：登录后的请求自动携带凭证，页面不用每次重复拼请求头：

  ```js
  request.interceptors.request.use((config) => {
    const token = getToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })
  ```

- **动手检查**：登录后在 Network 面板检查请求头；临时关闭后端再点列表页，观察“网络异常”提示；恢复后端并确认列表能加载。前端 API 地址和 FastAPI 端口必须一致。

## 第 09 节：开发用户注册功能

- **知识点**：前端“再次输入密码”只用于校验，不应提交到后端；后端用 Pydantic 验证用户名、邮箱和密码长度，用数据库唯一约束兜底。公开注册只能创建普通用户，不能接收前端自行指定的管理员角色。
- **源码入口**：[注册页面](fronted/src/views/register.vue)、[注册 API](fronted/src/api/auth.js)、[注册路由](backend/app/api/auth.py)、[用户请求模型](backend/app/schemas/user.py)。
- **关键代码**：`UserCreate` 校验输入，路由显式固定角色，避免用户在请求 JSON 中加 `is_superuser: true` 越权：

  ```python
  user = User(
      username=username,
      password=hash_password(data.password),
      email=str(data.email).lower(),
      is_active=True,
      is_superuser=False,
  )
  ```

- **动手检查**：尝试重复用户名、重复邮箱、两次密码不同；在 `/docs` 直接请求注册接口并附加管理员字段，确认注册结果仍是普通用户。注意前端校验可被绕过，后端校验才是边界。

## 第 10 节：开发后端文件上传 API 接口

- **知识点**：浏览器用 `FormData` 传 `multipart/form-data`；FastAPI 用 `UploadFile` 接收；安全校验要同时看 MIME、文件大小和实际内容；保存文件名用随机 UUID，公开访问路径由静态文件挂载提供。
- **源码入口**：[上传接口](backend/app/api/upload.py)、[静态目录挂载](backend/app/main.py)、[前端上传封装](fronted/src/api/user.js)、[上传界面](fronted/src/views/user.vue)。
- **关键代码**：读取 `MAX_IMAGE_SIZE + 1` 字节可在不无限制读入内存的情况下发现超限，不能只相信扩展名：

  ```python
  content = await file.read(MAX_IMAGE_SIZE + 1)
  if len(content) > MAX_IMAGE_SIZE:
      raise BusinessException(code=BizCode.BAD_REQUEST, message="图片大小不能超过 5MB")
  detected_suffix = detect_image_suffix(content)
  if not detected_suffix or detected_suffix != declared_suffix:
      raise BusinessException(code=BizCode.BAD_REQUEST, message="图片内容与文件类型不匹配")
  ```

- **动手检查**：上传真实 PNG/JPEG/WEBP、超过 5 MB 的图片，以及改名为 `.png` 的文本文件。当前页面上传成功后**只做预览**，并没有把头像 URL 保存到用户资料；这是“上传文件”与“持久化头像”两个不同功能。

## 第 11 节：开发用户修改个人信息功能

- **知识点**：`GET /api/user/info` 读取当前登录用户；`PUT /api/user/profile` 只修改自己的姓名和邮箱；邮箱要检查是否被其他用户占用。接口返回更新后的用户信息，前端同步更新共享状态。
- **源码入口**：[用户接口](backend/app/api/user.py)、[个人资料 Schema](backend/app/schemas/user.py)、[个人中心页面](fronted/src/views/user.vue)、[共享用户状态](fronted/src/utils/user.js)。
- **关键代码**：后端从 JWT 依赖获得 `current_user`，不接收客户端传来的目标用户 ID：

  ```python
  email_owner = db.query(User).filter(
      User.email == email, User.id != current_user.id
  ).first()
  if email_owner:
      raise BusinessException(code=BizCode.BAD_REQUEST, message="邮箱已被其他账号使用")
  current_user.email = email
  db.commit()
  ```

- **动手检查**：改自己的姓名和邮箱后刷新页面，验证显示仍正确；再尝试改为其他账号邮箱。解释为什么“自己是谁”应由 Token 决定，不能信任请求体里的 `user_id`。

## 第 12 节：开发用户修改密码功能

- **知识点**：改密要先验证旧密码，并拒绝新旧密码相同；数据库保存新密码哈希。前端改密成功后清理本地登录信息；后端 JWT 的密码版本指纹让旧 Token 失效。
- **源码入口**：[改密接口](backend/app/api/user.py)、[密码工具](backend/app/utils/password.py)、[JWT 版本指纹](backend/app/utils/jwt.py)、[前端改密表单](fronted/src/views/user.vue)。
- **关键代码**：先检查再更新；`hash_password` 每次产生用于存储的安全哈希：

  ```python
  if not verify_password(data.old_password, current_user.password):
      raise BusinessException(code=BizCode.BAD_REQUEST, message="原密码不正确")
  if data.old_password == data.new_password:
      raise BusinessException(code=BizCode.BAD_REQUEST, message="新密码不能与原密码相同")
  current_user.password = hash_password(data.new_password)
  db.commit()
  ```

- **动手检查**：测试错误旧密码、两次新密码不一致、正确修改；再拿修改前复制的 Token 请求 `/api/user/info`，应被拒绝并重新登录。

## 第 13 节：开发用户列表展示功能

- **知识点**：管理员接口通过 `Depends(get_current_admin)` 授权；`page/page_size/keyword` 是查询参数；`count()` 得到总数，`offset/limit` 切页；前端表格和分页器共享同一套查询状态。
- **源码入口**：[用户列表路由](backend/app/api/user.py)、[管理员权限依赖](backend/app/dependencies/permission.py)、[前端用户表格](fronted/src/views/user.vue)、[用户 API](fronted/src/api/user.js)。
- **关键代码**：页码从 1 开始，所以偏移量为 `(page - 1) * page_size`：

  ```python
  total = query.count()
  users = (
      query.order_by(User.id.desc())
      .offset((page - 1) * page_size)
      .limit(page_size)
      .all()
  )
  ```

- **动手检查**：管理员搜索用户名、姓名、邮箱并翻页；用普通用户 Token 直接请求 `/api/user`，应返回 403。仅在前端隐藏“用户管理”入口并不能保护接口。

## 第 14 节：开发用户增删改功能

- **知识点**：新增、更新、删除对应 POST/PUT/DELETE；更新 Schema 可选字段配合 `model_dump(exclude_unset=True)` 实现局部修改。当前编辑弹窗不提供重设用户名或密码，只修改邮箱、姓名、角色和启用状态。需要保护当前管理员不被自己禁用或取消权限；已有预约的用户删除可能触发外键约束，应提示改为禁用。
- **源码入口**：[管理员用户路由](backend/app/api/user.py)、[管理员 Schema](backend/app/schemas/user.py)、[前端用户弹窗](fronted/src/views/user.vue)。
- **关键代码**：只有请求中明确提供的字段才更新，避免默认值覆盖数据库原值：

  ```python
  update_data = data.model_dump(exclude_unset=True)
  for field, value in update_data.items():
      setattr(user, field, value)
  db.commit()
  ```

- **动手检查**：新增普通用户、修改姓名、禁用用户并测试其登录；取消删除确认框时数据不应变化。再思考：为什么“删除管理员自己”要在后端阻止？

## 第 15 节：开发实验室管理功能

- **知识点**：`Lab` 是数据库实体，`LabCreate/LabUpdate/LabResponse` 区分输入与输出；管理员做增删改，已登录用户可查询。`status=1` 表示开放，`status=0` 表示暂停；有关联设备或预约时，删除受外键约束，适合暂停开放。
- **源码入口**：[实验室模型](backend/app/models/lab.py)、[实验室 Schema](backend/app/schemas/lab.py)、[实验室接口](backend/app/api/lab.py)、[实验室页面](fronted/src/views/lab.vue)。
- **关键代码**：学生页面默认传 `only_open=true`，后端按条件过滤开放实验室：

  ```python
  query = db.query(Lab)
  if keyword.strip():
      query = query.filter(Lab.name.like(f"%{keyword.strip()}%"))
  if only_open:
      query = query.filter(Lab.status == 1)
  ```

- **动手检查**：管理员新增实验室、改容量、暂停开放；学生页面默认不显示暂停的实验室。注意当前接口的 `only_open` 是查询选项，不是学生端强制的后端数据权限。

## 第 16 节：开发实验室设备管理功能

- **知识点**：设备通过 `lab_id` 外键归属实验室；`joinedload(Equipment.lab)` 一次加载关联的实验室名称，避免列表逐项再查数据库；设备编号应唯一。`status` 和 `quantity` 共同决定是否可展示为可用。
- **源码入口**：[设备模型](backend/app/models/equipment.py)、[设备 Schema](backend/app/schemas/equipment.py)、[设备接口](backend/app/api/equipment.py)、[设备页面](fronted/src/views/equ.vue)。
- **关键代码**：`only_available` 同时检查正常状态与数量大于 0：

  ```python
  query = db.query(Equipment).options(joinedload(Equipment.lab))
  if lab_id:
      query = query.filter(Equipment.lab_id == lab_id)
  if only_available:
      query = query.filter(Equipment.status == 1, Equipment.quantity > 0)
  ```

- **动手检查**：给一个实验室新增两件设备，按实验室筛选；将其中一件数量改为 0，比较管理员列表与学生默认列表。

## 第 17 节：开发学生端实验室列表和设备列表

- **知识点**：一个 Vue 页面可按角色呈现两套操作：管理员可编辑，学生以浏览和预约为主；`computed(isAdmin)` 来源于共享用户状态。页面的 `v-if` 是展示逻辑，后端的 `get_current_admin` 才是写接口权限。
- **源码入口**：[共享角色状态](fronted/src/utils/user.js)、[主布局菜单](fronted/src/layouts/layouts.vue)、[实验室列表](fronted/src/views/lab.vue)、[设备列表](fronted/src/views/equ.vue)。
- **关键代码**：学生端默认只请求开放实验室和可用设备：

  ```js
  getLabListApi({ keyword: keyword.value, only_open: !isAdmin.value })
  getEquipmentListApi({
    lab_id: selectedLabId.value || undefined,
    keyword: keyword.value,
    only_available: !isAdmin.value
  })
  ```

- **动手检查**：分别用学生和管理员账号登录，记录相同页面的标题、按钮与数据差别；用普通用户 Token 直接尝试 POST `/api/labs`，确认后端仍返回 403。当前设备列表的“可用”过滤只检查设备自身的状态和数量，**不会再检查所属实验室是否开放**。

## 第 18 节：开发实验室预约功能

- **知识点**：预约请求包含实验室、日期、开始/结束时间和用途；Pydantic 检查开始早于结束；Service 统一承担开放状态、未来时间、时间冲突与数据库写入规则。普通接口和 AI 工具共用同一 Service，避免两套预约规则不一致。
- **源码入口**：[预约表单](fronted/src/views/lab.vue)、[预约请求模型](backend/app/schemas/reservation.py)、[预约接口](backend/app/api/reservation.py)、[预约业务服务](backend/app/services/reservation.py)。
- **关键代码**：两个半开时间段 `[开始, 结束)` 相交，当且仅当旧开始早于新结束且旧结束晚于新开始；`pending` 和 `approved` 都占用时段：

  ```python
  conflict = db.query(Reservation).filter(
      Reservation.lab_id == data.lab_id,
      Reservation.reservation_date == data.reservation_date,
      Reservation.status.in_(["pending", "approved"]),
      Reservation.start_time < data.end_time,
      Reservation.end_time > data.start_time,
  ).first()
  ```

- **动手检查**：分别提交完全重叠、部分重叠、前一单结束恰好等于下一单开始的预约，解释为什么前两种冲突而最后一种可相邻。MySQL 中创建预约时还会锁实验室行处理并发；SQLite 测试环境不模拟该锁。当前前端只向学生展示预约按钮，后端创建接口则允许**任意已登录用户**调用，这是展示逻辑与权限规则的区别。

## 第 19 节：开发我的预约与预约审核

- **知识点**：预约状态为 `pending / approved / rejected / cancelled`；学生只能看自己的预约、取消允许取消的状态；管理员看全部记录并对待审核记录通过或拒绝。取消与审核锁同一预约行，避免同时操作互相覆盖。
- **源码入口**：[预约记录模型](backend/app/models/reservation.py)、[预约列表/审核接口](backend/app/api/reservation.py)、[预约页面](fronted/src/views/reservation.vue)、[前端请求封装](fronted/src/api/reservation.js)。
- **关键代码**：审核前先确认当前状态仍是 `pending`；“通过”还要复核时间未过、实验室仍开放：

  ```python
  if reservation.status != "pending":
      raise BusinessException(code=BizCode.BAD_REQUEST, message="该预约已经处理")
  if data.status == "approved":
      # 代码随后复核预约日期、开始时间和实验室开放状态。
      ...
  ```

- **动手检查**：按“学生提交 → 管理员通过 → 学生查看”走一遍；再测试管理员拒绝、学生取消和重复审核。`status` 变化之后，旧按钮隐藏只是前端体验，后端仍要再次验证状态。

## 第 20 节：开发实验室 AI 助手对话（后端部分）

- **知识点**：对话接口也要 JWT 鉴权；`ChatRequest` 限制问题和历史消息长度，历史消息角色只能是 `user/assistant`，不能让客户端伪造 `system` 指令。一次请求要组织检索、工具、上下文与回答；这里的返回类型是 `text/event-stream`，不是普通 `Response.success()` JSON。
- **源码入口**：[对话请求模型](backend/app/schemas/ai.py)、[AI 路由](backend/app/api/ai.py)、[Agent 编排](backend/app/ai/agent.py)、[AI 配置](backend/app/config.py)。
- **关键代码**：`get_current_user` 先确定用户身份，生成器内创建并最终关闭数据库会话：

  ```python
  @router.post("/chat/stream")
  def chat_stream(data: ChatRequest, current_user: User = Depends(get_current_user)):
      user_id = current_user.id
      history = [item.model_dump() for item in data.history]
      # 后续由 generate_events() 逐段输出 SSE。
  ```

- **动手检查**：用 ApiPost 给请求设置或不设置 `Authorization: Bearer <JWT>`，比较调用 `/api/ai/chat/stream` 的结果。注意这里使用的是**用户登录 JWT**，不是模型服务商的 API Key；模型 Key 只应由后端读取。当前 `/api/auth/login` 接收 JSON，Swagger 的标准 OAuth2 密码表单不等同于这个登录接口。

## 第 21 节：开发实验室 AI 助手对话（前端与联调）

- **知识点**：聊天页维护消息数组、过程提示和发送状态；历史应在加入当前问题及空白回答**之前**截取；前端使用 `fetch` 读取 POST 响应流，用 `AbortController` 允许停止。由于这一路没有经过 axios 拦截器，401 要单独处理。
- **源码入口**：[聊天页面](fronted/src/views/chat.vue)、[流式请求封装](fronted/src/api/ai.js)、[AI 路由](backend/app/api/ai.py)。
- **关键代码**：回复对象是响应式的，每收到一段 `token` 都追加到同一条回答；停止时中止当前请求：

  ```js
  const assistantMessage = reactive({ role: 'assistant', content: '', events: [] })
  messages.value.push(assistantMessage)
  // streamChatApi 的事件回调中：
  if (eventName === 'token') assistantMessage.content += data.content
  ```

- **动手检查**：询问“实验室预约规则”，观察页面先显示过程提示，再逐段出现答案；点击“停止”观察请求中止。此接口需要 POST body 和 Authorization，不能直接改用浏览器原生 `EventSource`。

## 第 22 节：用 RAG 给实验室助手接入知识库

- **知识点**：RAG 是“先检索相关资料，再把资料放进模型上下文”；本项目把 `knowledge/*.md` 作为知识源，ChromaDB 保存索引；文件内容哈希用于增量同步新增、修改和删除。当前 `build_local_embedding()` 是**离线的字符/双字符哈希向量**，不是 OpenAI Embeddings，也不是生产级语义向量模型；Markdown 会按段落分块后写入索引（每块约 200～400 字，块 ID 形如 `safety_chunk0`），但切分策略简单，也没有相似度阈值。
- **源码入口**：[知识库实现](backend/app/ai/knowledge.py)、[预约规则文档](backend/app/knowledge/lab_rules.md)、[设备规范文档](backend/app/knowledge/equipment_guide.md)、[索引同步测试](backend/tests/test_knowledge.py)。
- **关键代码**：查询时使用与建索引时相同的向量算法；ChromaDB 失败则回退到关键词检索，不影响其他业务：

  ```python
  result = collection.query(
      query_embeddings=[build_local_embedding(query)],
      n_results=min(limit, document_count),
  )
  # 异常分支返回 simple_search(query, limit)
  ```

- **动手检查**：阅读两份 Markdown，再运行 `test_knowledge.py`，观察新增、修改、删除文档如何同步索引。思考为什么知识库更新不等于修改 MySQL 业务数据，以及为什么正式项目通常需要“切块 + 更合适的中文 Embedding”。

## 第 23 节：用 Tool Calling 让助手查询实验室数据

- **知识点**：模型返回的是“建议调用哪个工具及参数”，真正查询或写入 MySQL 的仍是后端 Python 函数。本项目提供十个工具（`list_open_labs`、`search_lab_docs`、`list_lab_equipments`、`get_latest_announcements`、`get_my_reservations`、`check_lab_availability`、`recommend_lab`、`get_today`、`cancel_reservation`、`create_lab_reservation`）；写工具必须再次执行服务端校验，不能只信模型生成的参数或提示词。
- **源码入口**：[工具定义与实现](backend/app/ai/tools.py)、[模型工具分发](backend/app/ai/agent.py)、[统一预约服务](backend/app/services/reservation.py)。
- **关键代码**：模型选择创建预约时，后端还要检查用户当前轮有明确预约意图，且本轮最多处理一次写入：

  ```python
  for tool_call in tool_calls:
      name = tool_call.function.name
      arguments = json.loads(tool_call.function.arguments or "{}")
      if name == "create_lab_reservation" and write_tool_handled:
          result = "本轮已经处理过一次预约请求，没有重复创建。"
      else:
          # _execute_tool 内部：写预约前再检查当前轮是否明确确认
          result = _execute_tool(name, arguments, db, user_id, message)
          if name == "create_lab_reservation":
              write_tool_handled = True
  ```

- **动手检查**：比较“有哪些开放实验室”“预约实验室ID 1 …”“不要帮我预约”三类输入会走的分支。注意：没有模型 Key 时用本地规则选择工具；配置 Key 后由模型通过 Chat Completions Tool Calling 选择工具（图内 `agent_node` 与图外 `run_model_tools` 两条路径），该真实模型路径目前尚未用用户 Key 实测。

## 第 24 节：用 LangGraph 做智能预约 Agent

- **知识点**：`AgentState` 是节点之间共享的数据结构；当前图是**循环拓扑** `retrieve → agent ⇄ tools → END`：先检索知识，再进入 `agent` 节点——没有 Key 时退化为本地规则（`local_tool_node`），有 Key 时由模型选择工具，`tools` 节点执行后经条件边（`should_continue`）回到 `agent`。LangGraph 不可用时会按顺序执行回退逻辑，便于本地学习；图外还有 `run_model_tools()`，负责把模型工具过程以 `tool_start`/`tool_end` 事件暴露给 SSE。
- **源码入口**：[状态、节点与建图](backend/app/ai/agent.py)、[AI 请求编排](backend/app/api/ai.py)、[架构图](ARCHITECTURE.md)。
- **关键代码**：边的顺序决定数据流，`retrieve_node` 写入 `retrieved_docs`，下一节点才能读取它：

  ```python
  graph = StateGraph(AgentState)
  graph.add_node("retrieve", retrieve_node)
  graph.add_node("agent", agent_node)
  graph.add_node("tools", execute_tools_node)
  graph.set_entry_point("retrieve")
  graph.add_edge("retrieve", "agent")
  graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
  graph.add_edge("tools", "agent")
  ```

- **动手检查**：手画本项目的循环图，标出 `retrieve`/`agent`/`tools` 各节点读写的 `AgentState` 字段，说明 `should_continue` 何时去 `tools`、何时 `END`；再定位图外的 `run_model_tools()`，区分它和图内工具节点的分工。

## 第 25 节：用 SSE 流式输出并让过程可见

- **知识点**：SSE 事件用 `event:`、`data:` 和空行分隔；后端依次发 `status`、可选的 `tool_start`/`tool_end` 与 `tool`、多个 `token`、最后 `done`，失败时发 `error`。前端按 UTF-8 流逐块解码，保留未完整到达的事件片段；一个网络数据块不一定刚好是一条 SSE 事件。
- **源码入口**：[SSE 生成](backend/app/api/ai.py)、[前端 SSE 解析](fronted/src/api/ai.js)、[过程显示与取消](fronted/src/views/chat.vue)、[本地/模型回答分支](backend/app/ai/agent.py)。
- **关键代码**：后端每条事件以两个换行结束；前端只有收齐完整事件块才解析：

  ```python
  def sse_event(event: str, data: dict) -> str:
      return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
  ```

- **动手检查**：在浏览器 Network 中观察响应事件；解释为什么前端需要 `buffer.split(/\r?\n\r?\n/)`。无 Key 时后端按每 12 个字符分片展示，**不是真实模型 token**；有 Key 时才处理模型的流式增量（`delta.content`）。

## 第 26 节：完善系统首页与课程收尾

- **知识点**：首页统计是聚合查询：开放实验室数量、正常设备总量、预约数量和待审核数量；学生的预约数据范围限制为自己，管理员可看全局且多一个用户总数。前端用 `computed` 依据角色渲染不同卡片，但数据权限仍由后端控制。
- **源码入口**：[统计接口](backend/app/api/stats.py)、[统计请求函数](fronted/src/api/stats.js)、[首页](fronted/src/views/home.vue)、[运行说明](README.md)、[完成进度](PROGRESS.md)。
- **关键代码**：对同一个统计查询附加当前用户过滤，防止学生看到全局预约数量：

  ```python
  if not current_user.is_superuser:
      reservation_query = reservation_query.filter(Reservation.user_id == current_user.id)
      pending_query = pending_query.filter(Reservation.user_id == current_user.id)
  ```

- **动手检查**：分别用管理员和学生账号查看首页，核对预约统计与菜单差异；运行 `npm run build` 和后端单元测试。不要把“前端少展示一个卡片”当成后端数据隔离。

## 第 27 节：项目图解与完整链路复盘

- **知识点**：从系统全景、代码映射、登录时序、预约时序和 AI 流程五个角度理解模块关系。阅读时先确定“谁发请求、谁校验、谁写数据、谁返回结果”，再回到具体函数。
- **源码入口**：[完整项目图解](ARCHITECTURE.md)、[前端路由](fronted/src/router/index.js)、[后端路由](backend/app/api/__init__.py)、[预约服务](backend/app/services/reservation.py)、[AI Agent](backend/app/ai/agent.py)。
- **关键代码**：把第 00 节的入口与第 18、23 节的业务连接起来：

  ```text
  用户 → Vue 页面 → src/api → FastAPI /api/... → 鉴权/参数校验
       → Service/ORM → MySQL → 前端更新状态

  AI 问题 → /api/ai/chat/stream → RAG + 工具上下文
          → 本地分片或模型回答 → SSE → chat.vue
  ```

- **动手检查**：任选一条普通预约和一条 AI 问答，从浏览器事件追到数据库或知识库，再追到返回界面。图解中的工具箭头表达的是**概念关系**；精确执行顺序请以第 24 节的源码为准。

## 学完后的自检清单

- 能解释 `fronted/src/views`、`src/api`、`src/utils/request.js` 各自负责什么，而不是把所有请求都写在页面里。
- 能说清 401（未登录/凭证失效）与 403（已登录但无权限）的区别，并找到后端对应的 `Depends`。
- 能画出预约的 `pending → approved/rejected` 以及可取消的状态，并证明时间冲突公式为何正确。
- 能区分 MySQL 业务数据、Markdown 知识源和 ChromaDB 索引的职责。
- 能说明 LangGraph 循环图（`retrieve → agent ⇄ tools`）里各节点的职责、无 Key 时本地规则的作用，以及本地分片输出和真实模型 SSE 的区别。
- 能独立运行构建与测试，并知道真实模型调用尚需自己配置后端 API Key 与可用额度。

如果要进一步练习，可优先选择一个小扩展：把上传 URL 真正保存为用户头像、为管理员增加“重设用户密码”专用接口、为 RAG 接入更合适的中文 Embedding 和相似度阈值，或用真实模型 Key 实测 Tool Calling 全链路。上述都是**后续练习方向**，不是当前已经实现的功能。
