# 智能实验室预约系统：第 00–27 节知识点复习与详解

> 这份是**学完每节课后的纯概念复习笔记**，不是首次学习入口。首次学习请打开 [`LEARN_WITH_CODE.md`](LEARN_WITH_CODE.md)，那里每个知识点后都紧跟项目代码、逐句解析和复现检查。
>
> 本文件用于在学完代码后检查自己能否讲清四件事：**是什么、为什么需要它、在这个项目里具体怎么用、容易踩什么坑**。
>
> 用法：学完一节课，翻到对应节，先遮住「详解」自己回忆，再看解释对照。想查某个知识点的**完整代码**，看每节末尾的「代码落点」链接，跳到四份分册里的完整源码。
>
> 四份分册（`00-08-foundation.md` / `09-14-users.md` / `15-19-business.md` / `20-27-ai.md`）用于查看大段完整源码；本笔记只用于复习概念。
>
> **安全约定：** 密钥只写在 `backend/.env`；不要把 Key 写进 `VITE_` 变量、粘贴到聊天记录或提交到仓库；不要抄真实 Token；数据库只存 bcrypt 哈希；验证用指定测试账号，不要清空或重建已有 MySQL 数据。

## 目录

- 第一部分 工程骨架与登录联调（第 00–08 节）
- 第二部分 用户功能（第 09–14 节）
- 第三部分 业务（第 15–19 节）
- 第四部分 AI 助手（第 20–27 节）

---

# 第一部分：工程骨架与登录联调

## 第 00 节：认识完整项目与一次请求

### 知识点 ①：把系统拆成四层

- **是什么**：一个前后端分离项目，逻辑上分成「前端交互、后端接口、数据库业务、AI 助手」四块。前端管页面长什么样、用户点什么；后端管接口和校验；数据库存数据；AI 管智能问答。
- **为什么**：拆开以后每层能单独改、单独测。改前端样式不用动数据库，改预约规则不用动页面。这也是「前后端分离」的意义——前端和后端是两个独立的程序，靠 HTTP 通信。
- **项目里怎么用**：`fronted/` 是 Vue 前端，`backend/` 是 FastAPI 后端。前端发起请求，后端处理后返回 JSON。
- **易错点**：初学者常把「页面能显示」当成「功能完成」。实际上页面显示的数据只是前端自己拼的，真正能不能操作要看后端接口是否允许。

### 知识点 ②：一次请求的完整链路

- **是什么**：从你在浏览器点一下，到数据真正变化，中间要经过一串固定的环节。
- **为什么**：理解这条链，出错时才知道去哪个环节排查——是前端没发请求，还是后端 401 没通过，还是数据库写失败。
- **项目里怎么用**：主链路是 `Vue 页面 → src/api → axios → FastAPI 路由 → Pydantic/鉴权 → Service/ORM → MySQL`。
- **易错点**：遇到「接口没反应」，先分清是「请求根本没发出去」（看浏览器 Network 面板）还是「发出去被后端拒了」（看后端日志或响应状态码）。

> 代码落点：入口 [`backend/app/main.py`](../../backend/app/main.py)、路由汇总 [`backend/app/api/__init__.py`](../../backend/app/api/__init__.py)、前端路由 [`fronted/src/router/index.js`](../../fronted/src/router/index.js)。

## 第 01 节：环境、依赖与配置

### 知识点 ①：npm 与 Python 虚拟环境

- **是什么**：前端用 npm（Node 的包管理器）管依赖，`package.json` 记录装了什么；后端用 Python 虚拟环境（venv）隔离依赖，`requirements-all.txt` 记录后端依赖。
- **为什么**：依赖不隔离的话，两个项目可能要求同一个库的不同版本，互相打架。虚拟环境给每个项目一个独立的 Python 环境。
- **项目里怎么用**：前端 `npm run dev` 起 Vite 开发服务器；后端用 `.venv\Scripts\python.exe -m uvicorn app.main:app --reload` 起服务。`--reload` 让代码改动自动重启。
- **易错点**：起后端时别用全局 Python（可能没装依赖），要用项目自己的 `.venv` 里的解释器。

### 知识点 ②：环境变量与 `.env`

- **是什么**：把配置（数据库地址、密钥）放进 `.env` 文件，代码里通过配置类读取，而不是写死在代码里。
- **为什么**：① 密钥不能进仓库（提交了别人就看到了）；② 不同机器（本机、服务器）配置不同，改 `.env` 就行，不用改代码。
- **项目里怎么用**：后端 `config.py` 用 `BaseSettings` 读 `backend/.env`；前端 Vite 只把 `VITE_` 开头的变量暴露给浏览器，所以前端 `.env` 里只能放接口地址。
- **易错点**：**密钥绝不能写进前端 `VITE_` 变量**——Vite 会把这些值打包进浏览器产物，任何访问网站的人都能看到。真实值只写本机 `backend/.env`。

### 知识点 ③：`package.json` 的 scripts 与依赖分类

- **是什么**：`scripts` 把常用命令起别名；`dependencies` 是运行时必须的库，`devDependencies` 只在开发/打包时用。
- **为什么**：别名让每个人敲同样短命令；依赖分类让部署时可以不装开发依赖，体积更小。
- **项目里怎么用**：`"dev"`、`"build"`、`"preview"` 三个脚本对应 Vite 的三个功能；`"type": "module"` 决定用 ESM（`import`）写法。
- **易错点**：`^` 表示「允许小版本升级」，`~` 表示「只允许补丁升级」；版本号写死到补丁号会让升级困难。

> 代码落点：[`fronted/package.json`](../../fronted/package.json)、[`fronted/vite.config.js`](../../fronted/vite.config.js)、[`backend/app/config.py`](../../backend/app/config.py)、[`backend/requirements-all.txt`](../../backend/requirements-all.txt)。

## 第 02 节：Vue 入口、路由与后台主框架

### 知识点 ①：`createApp` / `use` / `mount`

- **是什么**：`createApp(App)` 创建应用实例，`app.use(...)` 注册插件，`app.mount('#app')` 把应用挂到 HTML 的一个挂载点上。
- **为什么**：Vue 应用是一层一层「拼」起来的：根组件 → 装路由 → 装 UI 库 → 挂载。
- **项目里怎么用**：`main.js` 里装上 Element Plus（含全部图标）和路由，最后挂载到 `index.html` 的 `#app`。
- **易错点**：图标必须全量注册，否则模板里写 `<el-icon>` 会找不到组件。

### 知识点 ②：Vue Router 嵌套路由

- **是什么**：路由决定「URL 对应哪个组件」。嵌套路由（`children`）让一个父组件（布局）包住多个子页面。
- **为什么**：后台页都有共同的侧边栏 + 顶栏，抽成一个布局父组件，子页面只写自己的内容，不重复写框架。
- **项目里怎么用**：`layouts.vue` 是父级，主页、实验室、设备等 8 个页面作为 `children` 挂在它下面；`<router-view />` 负责把子页面渲染进布局的内容区。
- **易错点**：`App.vue` 里只有一级 `<router-view />`，真正的布局在 `layouts.vue`，别把菜单写在根组件里。

### 知识点 ③：路由守卫 `beforeEach`

- **是什么**：每次跳转前执行的一个函数，可以拦截或放行这次跳转。
- **为什么**：实现「未登录不能看受保护页面」，不必在每个页面里都写一遍判断。
- **项目里怎么用**：页面用 `meta.requiresAuth` 标记是否需要登录；守卫里判断有没有 Token——没 Token 且要去受保护页就跳到登录页，并带上 `redirect` 参数记住原来想去哪，登录成功后跳回去。
- **易错点**：守卫要处理**两个方向**：没 Token 去受保护页要拦；有 Token 还去登录页要放行去主页（否则登录完又跳回登录页）。

### 知识点 ④：懒加载 `() => import()`

- **是什么**：路由的组件用 `() => import('@/views/xxx.vue')` 动态引入，而不是顶部 `import`。
- **为什么**：打包时按页切分，访问到哪个页面才加载哪个，首屏更快。
- **项目里怎么用**：所有页面组件都用懒加载写法。
- **易错点**：这是「按需加载」，不是「异步组件」的全部含义；路由懒加载是它最常见的用法。

> 代码落点：[`fronted/src/main.js`](../../fronted/src/main.js)、[`fronted/src/App.vue`](../../fronted/src/App.vue)、[`fronted/src/router/index.js`](../../fronted/src/router/index.js)、[`fronted/src/layouts/layouts.vue`](../../fronted/src/layouts/layouts.vue)。

## 第 03 节：Vue 登录表单（响应式、校验、提交状态）

### 知识点 ①：`reactive` 与 `ref`

- **是什么**：两者都让数据变成「响应式」——数据一变，页面自动更新。`ref` 适合单个值，`reactive` 适合对象。
- **为什么**：不用响应式 API，改了数据页面不会刷新，就得手动操作 DOM，既麻烦又容易漏。
- **项目里怎么用**：表单对象用 `reactive`，`loading` 这类单个布尔用 `ref`。
- **易错点**：`ref` 在模板里自动解包（直接写 `loading`），在 `<script>` 里要写 `.value`。初学者常漏 `.value`。

### 知识点 ②：`computed` 与 `watch`

- **是什么**：`computed` 是根据其它数据算出来的值（有缓存，依赖不变就不重算）；`watch` 是监听某个值变化后执行副作用。
- **为什么**：派生值（比如「是否管理员」由 `userInfo` 推出）用 `computed` 最合适，不用手动同步。
- **项目里怎么用**：`isAdmin` 用 `computed(() => userInfo.value.is_superuser)`。
- **易错点**：`computed` 必须有返回值且是纯计算；要「值变了去请求接口」才用 `watch`。

### 知识点 ③：表单校验 `el-form` 的 `rules`

- **是什么**：给表单定义规则（必填、长度、格式），提交前用 `formRef.value.validate()` 触发校验。
- **为什么**：前端校验拦住明显的错，省一次无效请求；但前端校验只是体验，后端必须再校验一遍。
- **项目里怎么用**：`rules` 对象和 `reactive` 表单绑定；`validate()` 返回 Promise，`await ... .catch(() => false)` 拿到是否通过。
- **易错点**：两次密码一致、邮箱格式这类规则要写自定义 validator，不能只靠 `required`。

### 知识点 ④：`try/finally` 复位 loading

- **是什么**：loading 置 `true`，请求结束（无论成功失败）在 `finally` 里置 `false`。
- **为什么**：如果只在成功分支复位，请求失败时按钮会一直转圈。
- **项目里怎么用**：所有提交类操作都是 `loading = true; try { ... } finally { loading = false }`。
- **易错点**：`finally` 一定要写，这是本项目反复出现的固定套路。

### 知识点 ⑤：共享用户状态（模块级单例）

- **是什么**：`userInfo` 这个 `ref` 定义在 `useUser()` 函数**外面**，导出的 `useUser` 每次调用都返回同一个对象。
- **为什么**：如果定义在函数里面，每次调用 `useUser()` 都会新建一份，各组件各改各的，登录后顶栏和内容区对不上。
- **项目里怎么用**：`utils/user.js` 里 `const userInfo = ref(null)` 在函数外，`useUser()` 返回它和它的派生值。
- **易错点**：这是本项目最重要的前端知识点之一——「共享状态」靠的是「模块单例」，不是靠全局变量名。

> 代码落点：[`fronted/src/views/login.vue`](../../fronted/src/views/login.vue)、[`fronted/src/utils/user.js`](../../fronted/src/utils/user.js)、[`fronted/src/api/auth.js`](../../fronted/src/api/auth.js)。

## 第 04 节：FastAPI 入口、数据库依赖与 CORS

### 知识点 ①：FastAPI 应用与 CORS

- **是什么**：`FastAPI()` 创建应用；`CORSMiddleware` 让浏览器允许前端跨域访问后端。
- **为什么**：前端跑在 5173，后端跑在 8000，这是两个不同「源」，浏览器默认禁止跨域请求，必须后端明确放行。
- **项目里怎么用**：只放行 `http://localhost:5173` 和 `http://127.0.0.1:5173` 两个源。
- **易错点**：不能图省事写 `allow_origins=["*"]` 同时又开 `allow_credentials=True`——这是错误配置，浏览器会拒绝。

### 知识点 ②：静态文件挂载 `StaticFiles`

- **是什么**：把服务器上的一个目录通过一个 URL 前缀暴露出来，浏览器能直接访问里面的文件。
- **为什么**：上传的头像等文件要能被前端通过 URL 预览，而不是每次走接口读。
- **项目里怎么用**：`app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR))`，上传后的图片就能用 `/uploads/xxx.png` 访问。
- **易错点**：目录要先存在；挂载的 URL 前缀要同时写进 CORS 允许范围（同源则不必）。

### 知识点 ③：SQLAlchemy 引擎、会话、`get_db` 依赖

- **是什么**：`engine` 是数据库连接池，`SessionLocal` 是会话工厂，`get_db` 用 `yield` 提供一个请求级会话，请求结束自动关闭。
- **为什么**：每个请求用独立会话，用完关掉，避免连接泄漏；`yield` 让 FastAPI 在请求结束时执行 `finally` 关闭。
- **项目里怎么用**：接口函数里写 `db: Session = Depends(get_db)` 就拿到会话；`get_db` 里 `try: yield db finally: db.close()`。
- **易错点**：`pool_pre_ping=True` 让连接池在拿到连接前先探活，避免用上已断开的连接。

### 知识点 ④：ORM 基类 `Base` 与 `create_all`

- **是什么**：`Base(DeclarativeBase)` 是所有模型的父类，公共列（id、创建时间、更新时间）写在这里；`Base.metadata.create_all(engine)` 把没建的表建出来。
- **为什么**：每个模型都要有 id 和时间戳，抽到父类避免重复；`create_all` 让启动时自动建表。
- **项目里怎么用**：`database.py` 定义 `Base`，各模型继承它；`main.py` 里调 `create_all`。
- **易错点**：`create_all` 只建**尚不存在**的表，不修改已有表结构；改字段要手动迁移。模型必须被 import 过才会注册进 `metadata`，所以 `models/__init__.py` 要汇总导入。

> 代码落点：[`backend/app/main.py`](../../backend/app/main.py)、[`backend/app/database.py`](../../backend/app/database.py)、[`backend/app/api/__init__.py`](../../backend/app/api/__init__.py)、[`backend/app/models/user.py`](../../backend/app/models/user.py)。

## 第 05 节：登录 API（校验、查用户、密码哈希）

### 知识点 ①：Pydantic `BaseModel` 与 `Field`

- **是什么**：Pydantic 模型定义请求体的结构和校验规则；`Field(min_length=...)` 声明约束。
- **为什么**：FastAPI 收到请求会自动用模型校验，不合规的直接 422，不会进业务代码。
- **项目里怎么用**：`LoginRequest` 定义用户名、密码的最小长度；`LoginResponse` 声明返回 Token 和用户信息。
- **易错点**：输入模型和输出模型要分开，别用一个类复用——输出可能想隐藏某些字段。

### 知识点 ②：bcrypt 密码哈希

- **是什么**：把密码做单向加密存进数据库；登录时把输入的密码同样加密后比对，而不是解密。
- **为什么**：数据库被盗时，哈希比明文难还原；`gensalt()` 每次生成不同盐，同一密码两次哈希结果也不同，防止彩虹表破解。
- **项目里怎么用**：`hash_password` 存哈希，`verify_password` 用 `checkpw` 校验。
- **易错点**：**数据库只能存哈希，绝不能存明文**；响应体里也永远不能带 `password` 字段。

### 知识点 ③：登录失败不区分原因

- **是什么**：用户名不存在和密码错误，返回同一句提示。
- **为什么**：如果提示「用户名不存在」，攻击者就能用穷举猜出哪些用户名是真实存在的（账号枚举攻击）。
- **项目里怎么用**：登录接口对这两种情况返回一样的错误消息。
- **易错点**：这看起来反直觉，但安全上很重要。

> 代码落点：[`backend/app/schemas/auth.py`](../../backend/app/schemas/auth.py)、[`backend/app/utils/password.py`](../../backend/app/utils/password.py)、[`backend/app/api/auth.py`](../../backend/app/api/auth.py)。

## 第 06 节：JWT 签发、Bearer 鉴权与管理员权限

### 知识点 ①：JWT 是什么

- **是什么**：一段带签名的 Token，里面「装」着一些信息（比如 user_id、过期时间），服务端签好发给客户端，客户端每次请求带回来。
- **为什么**：服务端不用存会话（无状态），只要验签名没过期、签名没被篡改，就信 Token 里的内容。
- **项目里怎么用**：`create_access_token` 用 `jwt.encode` 签发；`decode_access_token` 用 `jwt.decode` 解析。
- **易错点**：JWT 的 payload 是「可读」的（base64），所以**不能放敏感信息**，只放 user_id 这类标识。

### 知识点 ②：`password_version` 让改密后旧 Token 失效

- **是什么**：Token 里带一个「密码版本号」，它是 bcrypt 哈希的 SHA-256 指纹；改密码后哈希变了，指纹也变，旧 Token 里的版本号对不上，自然失效。
- **为什么**：JWT 本身「无状态」，正常改密后旧 Token 仍有效（因为没过期）。带上版本号，改密就能强制所有旧 Token 作废。
- **项目里怎么用**：`build_password_version` 算指纹，写进 Token；鉴权时用 `hmac.compare_digest` 比对。
- **易错点**：比对版本号要用 `hmac.compare_digest`（定时比较，防时序攻击），不能用 `==`。

### 知识点 ③：`OAuth2PasswordBearer` 与依赖注入

- **是什么**：`OAuth2PasswordBearer(tokenUrl=...)` 从请求头 `Authorization: Bearer xxx` 里取 Token；`Depends(get_current_user)` 让接口自动执行鉴权。
- **为什么**：鉴权逻辑抽成依赖，几十个接口复用，不用每个都写一遍取 Token 的代码。
- **项目里怎么用**：`dependencies/auth.py` 里 `get_current_user` 解 Token → 查用户 → 验状态和版本。
- **易错点**：依赖注入的好处是「复用 + 可测试」，不是「自动帮你加 Token」。

### 知识点 ④：401 与 403 的区别

- **是什么**：401 表示「你没登录 / 凭证无效」，403 表示「你登录了但没权限」。
- **为什么**：两者语义不同，前端处理也不同（401 跳登录，403 提示没权限）。
- **项目里怎么用**：`get_current_user` 失败返回 401；`get_current_admin` 里非管理员返回 403。
- **易错点**：初学者常混用。记口诀：**401 是「你是谁我不知道」，403 是「我知道你是谁，但你不许」**。

> 代码落点：[`backend/app/utils/jwt.py`](../../backend/app/utils/jwt.py)、[`backend/app/dependencies/auth.py`](../../backend/app/dependencies/auth.py)、[`backend/app/dependencies/permission.py`](../../backend/app/dependencies/permission.py)。

## 第 07 节：统一响应与全局异常处理

### 知识点 ①：统一响应体 `{code, message, data}`

- **是什么**：所有接口返回同一个结构，`code` 是业务码，`message` 是提示，`data` 是真正的数据。
- **为什么**：前端不用为每个接口写不同的解析逻辑，看到 `code` 就能统一处理成功/失败。
- **项目里怎么用**：`common/response.py` 里 `BizCode` 枚举业务码，`Response` 提供 `success` / `fail` 快捷构造。
- **易错点**：业务码（`BizCode`）和 HTTP 状态码是两套东西，别混；但两者要约定对应关系。

### 知识点 ②：四个全局异常处理器

- **是什么**：用 `@app.exception_handler` 注册处理器，把业务异常、HTTP 异常、参数校验失败、未知异常统一转成上面的响应结构。
- **为什么**：不写处理器的话，异常会返回 FastAPI 默认格式，和统一响应结构不一致，前端难处理。
- **项目里怎么用**：`common/exceptions.py` 里 `business_exception_handler` 等四个函数，业务异常时 HTTP 状态码从业务码推导（400-599 直接用，否则兜底 500）。
- **易错点**：**未知异常只对内记日志，对外给通用提示，不能把堆栈返回给前端**——堆栈会泄露文件路径和实现细节。

> 代码落点：[`backend/app/common/response.py`](../../backend/app/common/response.py)、[`backend/app/common/exceptions.py`](../../backend/app/common/exceptions.py)。

## 第 08 节：axios 封装与前后端联调

### 知识点 ①：axios 实例

- **是什么**：`axios.create({ baseURL, timeout })` 创建一个统一配置的实例，业务都用它，不直接 `axios.get`。
- **为什么**：基地址、超时、拦截器配一次，全局生效。
- **项目里怎么用**：`utils/request.js` 里创建实例，`api/*.js` 都 `import request`。
- **易错点**：别在组件里直接 `axios.post`，统一走封装，才能吃到拦截器。

### 知识点 ②：请求拦截器与响应拦截器

- **是什么**：请求拦截器在发出前改配置（加 Token）；响应拦截器在收到后统一处理（解包 data、报错提示）。
- **为什么**：Token 不用每个接口手动加；错误提示不用每个地方写一遍。
- **项目里怎么用**：请求拦截器加 `Authorization: Bearer`；响应拦截器直接 `return response.data`，并处理三类错误——401 跳登录、超时提示、网络不可达提示。
- **易错点**：401 跳转要带上当前路径作为 `redirect`，登录后跳回；跳之前先判是否已在登录页，避免死循环。

### 知识点 ③：Token 统一存取

- **是什么**：把 Token 的读取、写入、清除收进 `utils/auth.js`。
- **为什么**：组件不直接操作 `localStorage`，将来换存储方案只改一个文件。
- **项目里怎么用**：`getToken` / `setToken` / `removeToken` / `logout`；`logout` 同时清 Token 和用户信息。
- **易错点**：只清 Token 不清用户信息，会残留「上一账号」的头像昵称。

> 代码落点：[`fronted/src/utils/request.js`](../../fronted/src/utils/request.js)、[`fronted/src/utils/auth.js`](../../fronted/src/utils/auth.js)、[`fronted/src/api/auth.js`](../../fronted/src/api/auth.js)。

# 第二部分：用户功能

## 第 09 节：开发用户注册功能

### 知识点 ①：`field_validator` 去空白再校验

- **是什么**：Pydantic 的字段校验器，在字段赋值后执行自定义校验。
- **为什么**：只写 `min_length=2` 拦不住「两个空格」——空格也算字符。先 `strip()` 去掉两端空格，再判长度，才能真正拦住「全空格」这类输入。
- **项目里怎么用**：用户名校验器先 `strip` 再判长度，非法时 `raise ValueError`。
- **易错点**：校验器要返回处理后的值（`return cleaned`），否则字段会是 None。

### 知识点 ②：`model_validator(mode="after")` 跨字段校验

- **是什么**：在模型整体构建完成后执行的校验器，能同时看到多个字段。
- **为什么**：有些规则涉及多个字段（比如两次密码一致），单字段校验器做不到，需要 `after` 模式看整个对象。
- **项目里怎么用**：改密模型里校验「两次新密码一致」；更新模型里用它配合 `model_fields_set` 拒绝显式传 null。
- **易错点**：`mode="after"` 的校验器要返回 `self`；`before` 模式返回的是 dict。

### 知识点 ③：`model_fields_set` 区分「没传」和「传了 null」

- **是什么**：Pydantic v2 里记录「哪些字段被显式传入」的集合。
- **为什么**：更新接口要支持「只传要改的字段」，但「没传某个字段」和「把字段改成 null」是两回事——后者可能把数据库必填列写坏。
- **项目里怎么用**：更新模型里检查「字段在 `model_fields_set` 里且值为 None」就报错。
- **易错点**：这是「局部更新」安全性的关键，也是本项目最容易漏的理解点。

### 知识点 ④：`EmailStr` 与 `IntegrityError`

- **是什么**：`EmailStr` 校验邮箱格式（需装 `email-validator`）；`IntegrityError` 是数据库唯一约束冲突时抛的异常。
- **为什么**：邮箱格式在进库前拦；但「唯一」约束最终由数据库保证——两个请求同时注册同名，应用层查重可能都查不到，数据库的 `unique` 是最后一道防线。
- **项目里怎么用**：注册接口先查重，再 try/except 捕获 `IntegrityError` 并 `rollback()`。
- **易错点**：捕获 `IntegrityError` 后必须 `rollback()`，否则会话处于失败状态不能继续用。

### 知识点 ⑤：公开注册不能自我提权

- **是什么**：注册接口里 `is_superuser=False` 写死，不从请求体取。
- **为什么**：如果接受请求里的 `is_superuser`，任何人都能注册一个管理员账号，整个系统就白做了。
- **项目里怎么用**：`register()` 里硬编码 False。
- **易错点**：凡是「角色」「权限」这类字段，公开接口一律写死，只有管理员接口能改。

> 代码落点：[`backend/app/schemas/user.py`](../../backend/app/schemas/user.py)、[`backend/app/api/auth.py`](../../backend/app/api/auth.py)、[`fronted/src/views/register.vue`](../../fronted/src/views/register.vue)。

## 第 10 节：开发文件上传 API

### 知识点 ①：`UploadFile` 与有界读取

- **是什么**：FastAPI 用 `UploadFile = File(...)` 接收上传文件；读取时先读 `MAX_IMAGE_SIZE + 1` 个字节。
- **为什么**：多读 1 字节，如果读到了，说明超过上限，直接拒绝——这样不用把整个大文件读进内存，防止内存被打爆。
- **项目里怎么用**：`upload.py` 里 `content = await file.read(MAX_IMAGE_SIZE + 1)`，超了就报错。
- **易错点**：别用 `await file.read()` 无上限地读整个文件。

### 知识点 ②：魔数嗅探真实类型

- **是什么**：读文件头几个字节（魔数），判断它到底是什么格式。
- **为什么**：客户端可以随便改 `content_type`，把恶意文件说成图片；文件头字节不会说谎。
- **项目里怎么用**：`detect_image_suffix` 检查 PNG/JPEG 等的魔数字节，判断真实后缀。
- **易错点**：**类型判断必须基于文件内容（魔数），不能只信客户端传来的 `content_type`**。

### 知识点 ③：UUID 文件名与路径安全

- **是什么**：上传的文件用随机 UUID 重命名，不用用户提供的原始文件名。
- **为什么**：原始文件名可能带 `../`（路径穿越，写到别的目录）或和已有文件重名；UUID 是随机的，避免这两类问题。
- **项目里怎么用**：`uuid4().hex + 后缀` 生成新文件名。
- **易错点**：文件名永远用后端生成的，前端传的文件名只当参考甚至忽略。

> 代码落点：[`backend/app/api/upload.py`](../../backend/app/api/upload.py)、[`fronted/src/api/user.js`](../../fronted/src/api/user.js)、[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue)。

## 第 11 节：修改个人信息与共享用户状态

### 知识点 ①：`model_dump(exclude_unset=True)` 局部更新

- **是什么**：把模型转成 dict，但只包含「客户端真正传了的字段」。
- **为什么**：更新接口用 PATCH 语义，客户端只传要改的字段，没传的字段保持原值，而不是被设成 null。
- **项目里怎么用**：`update_data = data.model_dump(exclude_unset=True)`，然后 `setattr` 逐个赋值。
- **易错点**：忘写 `exclude_unset=True` 会把没传的字段设成默认值（通常是 None），覆盖掉数据库里的原值。

### 知识点 ②：`joinedload` 预加载关联对象

- **是什么**：查询时用一次 JOIN 把关联对象一起取出来。
- **为什么**：不预加载的话，遍历列表时每个对象再查一次数据库（N+1 问题）——100 条数据会查 101 次。
- **项目里怎么用**：用户列表等场景用 `.options(joinedload(...))` 一次取回关联。
- **易错点**：列表接口（会返回多条）才需要关心 N+1；单条查询影响小。

### 知识点 ③：保存后同步共享状态

- **是什么**：改完个人资料后，把新值写回共享的 `userInfo`，让顶栏等其它地方一起变。
- **为什么**：`userInfo` 是模块级单例，改它一处，所有用它的组件都会更新。
- **项目里怎么用**：`saveProfile` 成功后重新拉取用户信息或直接更新 `userInfo`。
- **易错点**：不更新的话，顶栏显示的还是旧名字，要刷新页面才对。

> 代码落点：[`backend/app/api/user.py`](../../backend/app/api/user.py)、[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue)。

## 第 12 节：修改密码与旧 Token 失效

### 知识点 ①：改密要校验旧密码

- **是什么**：改密接口要求先传对旧密码，才允许改。
- **为什么**：防止「别人拿到你的 Token 就直接改你的密码」——Token 被盗还能改密，账号就彻底丢了。
- **项目里怎么用**：`UserPasswordUpdate` 含 `old_password`，接口里 `verify_password` 校验。
- **易错点**：改密是敏感操作，旧密码校验不能省。

### 知识点 ②：改密后旧 Token 自动失效

- **是什么**：改密后 `password_version` 变了，所有旧 Token 里的版本号对不上，立即失效。
- **为什么**：改密通常意味着「密码可能泄露了」，应该强制所有已登录设备重新登录。
- **项目里怎么用**：改密成功后，前端清 Token 并跳登录页；后端鉴权也因版本不符拒旧 Token。
- **易错点**：这是第 06 节 `password_version` 的实际应用，前后端要配合——前端清凭证，后端验版本。

> 代码落点：[`backend/app/api/user.py`](../../backend/app/api/user.py)、[`backend/app/utils/jwt.py`](../../backend/app/utils/jwt.py)。

## 第 13 节：管理员用户列表

### 知识点 ①：分页

- **是什么**：列表接口接受 `page`、`page_size` 参数，只返回当前页，同时返回总数。
- **为什么**：数据多了不能一次全返回，分页既省流量也省内存。
- **项目里怎么用**：`Query` 收分页参数，`offset` / `limit` 控制 SQL 范围，`count()` 算总数。
- **易错点**：前端要同时拿到「当前页数据」和「总数」，才能算出一共几页。

### 知识点 ②：`el-table` 与 `el-pagination`

- **是什么**：Element Plus 的表格和分页组件。
- **为什么**：表格处理列、状态标签、作用域插槽；分页处理页码切换。
- **项目里怎么用**：`el-table` 用 `prop` 绑定字段，`#default="scope"` 拿到行数据做定制渲染；`el-pagination` 的 `current-change` 触发重新加载。
- **易错点**：页码或每页条数变化后都要重新调接口加载。

> 代码落点：[`backend/app/api/user.py`](../../backend/app/api/user.py)、[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue)。

## 第 14 节：管理员用户增删改

### 知识点 ①：对话框双模式（新增 / 编辑共用）

- **是什么**：一个 `el-dialog` 同时承担新增和编辑，用「有没有 id」区分模式。
- **为什么**：新增和编辑的表单几乎一样，共用一套表单和校验，省一半代码。
- **项目里怎么用**：`openUserDialog(user = null)`，`user` 为空是新增，非空是编辑；标题随模式切换。
- **易错点**：编辑模式下要处理「不改密码」——提交时剔除空密码字段。

### 知识点 ②：删除前的二次确认

- **是什么**：`ElMessageBox.confirm` 弹确认框，用户确认才删除。
- **为什么**：删除不可逆，误点就丢了数据。
- **项目里怎么用**：确认框的「取消」会 reject 这个 Promise，所以 `try { await confirm } catch { return }`。
- **易错点**：**不 catch 取消分支会报未处理的 Promise 拒绝**，这是 Element Plus 常见坑。

### 知识点 ③：不能删自己

- **是什么**：管理员删除接口里，目标 id 等于当前登录用户 id 时拒绝。
- **为什么**：防止管理员把自己删了，导致系统里没有管理员，自己也登不进来。
- **项目里怎么用**：`delete_user` 里比较 `user_id == current_user.id`。
- **易错点**：这类「自我保护」规则放在后端，不能只靠前端隐藏按钮。

> 代码落点：[`backend/app/api/user.py`](../../backend/app/api/user.py)、[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue)。

# 第三部分：实验室、设备与预约业务

## 第 15 节：开发实验室管理功能

### 知识点 ①：ORM 实体与字段约束

- **是什么**：用 Python 类描述数据库表，字段上的 `unique=True`、`nullable=False`、`default=...` 对应数据库约束。
- **为什么**：约束写进模型，建表时自动生效，且不用手写 SQL；`unique` 保证名称不重复，`default` 给服务端默认值。
- **项目里怎么用**：`Lab` 的 `name` 唯一、`status` 默认 1（开放）。
- **易错点**：`status` 这种「状态」字段用 0/1 或枚举，别用中文存——数字好比较、好扩展。

### 知识点 ②：输入/输出模型分离

- **是什么**：新增用 `LabCreate`（全字段必填校验）、更新用 `LabUpdate`（全可选）、返回用 `LabResponse`（含 id 和时间戳）。
- **为什么**：新增和更新校验规则不同（更新允许只传一部分），输出又要带上输入没有的字段（id、创建时间）。
- **项目里怎么用**：三个类各司其职，`LabResponse` 用 `ConfigDict(from_attributes=True)` 直接从 ORM 对象构造。
- **易错点**：别为了省事用一个类通吃，规则会互相打架。

### 知识点 ③：`only_open` 查询过滤

- **是什么**：列表接口接受 `only_open` 参数，为真时只返回 `status == 1` 的实验室。
- **为什么**：学生端只该看到可预约的，管理员要看全部（含暂停的）。
- **项目里怎么用**：前端按角色传 `only_open: !isAdmin.value`。
- **易错点**：**`only_open` 是查询选项，不是强制数据权限**——前端传不传都行，真正的权限拦截靠 `get_current_admin` 管写接口。

### 知识点 ④：删除受外键约束保护

- **是什么**：删除有设备或预约的实验室时，数据库外键约束会报错。
- **为什么**：不能删掉还有关联数据的实验室，否则设备和预约变成「孤儿」。
- **项目里怎么用**：删除接口捕获 `IntegrityError`，rollback 后提示「请改为暂停开放」。
- **易错点**：捕获后必须 rollback；给用户的提示要「可操作」（告诉他能怎么办），而不是把数据库错误原样抛给前端。

> 代码落点：[`backend/app/models/lab.py`](../../backend/app/models/lab.py)、[`backend/app/schemas/lab.py`](../../backend/app/schemas/lab.py)、[`backend/app/api/lab.py`](../../backend/app/api/lab.py)、[`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue)。

## 第 16 节：开发实验室设备管理

### 知识点 ①：外键 `ForeignKey` 与 `relationship`

- **是什么**：`lab_id = mapped_column(ForeignKey("labs.id"))` 让设备「属于」某个实验室；`lab = relationship("Lab")` 让你能从设备对象直接 `.lab` 拿到实验室对象。
- **为什么**：外键在数据库层保证引用完整；relationship 在 ORM 层提供方便的关联访问，不用手动 join。
- **项目里怎么用**：`Equipment` 同时有 `lab_id` 列和 `lab` 关系。
- **易错点**：`ForeignKey` 是「列」层面的外键，`relationship` 是「对象」层面的关联，两者常一起写但不是一回事。

### 知识点 ②：`joinedload` 避免 N+1

- **是什么**：`db.query(Equipment).options(joinedload(Equipment.lab))` 用 JOIN 一次取回设备和实验室。
- **为什么**：不预加载的话，取 100 台设备就要再查 100 次实验室（N+1 问题）。
- **项目里怎么用**：设备列表接口用 `joinedload`，`equipment_to_dict` 把实验室名摊平返回。
- **易错点**：这是第 11 节 `joinedload` 的业务版应用，规则一样——「返回多条的列表」才需要。

### 知识点 ③：`only_available` 过滤

- **是什么**：设备列表的「只看可用」，同时过滤 `status == 1`（正常）和 `quantity > 0`（有库存）。
- **为什么**：设备「可用」要同时满足两个条件：没在维护、数量不为 0。
- **项目里怎么用**：前端学生端传 `only_available: !isAdmin.value`。
- **易错点**：**`only_available` 只检查设备自身，不检查所属实验室是否开放**——这是有意为之，别当成 bug 去「修复」。

> 代码落点：[`backend/app/models/equipment.py`](../../backend/app/models/equipment.py)、[`backend/app/api/equipment.py`](../../backend/app/api/equipment.py)、[`fronted/src/views/equ.vue`](../../fronted/src/views/equ.vue)。

## 第 17 节：学生端与管理端的角色渲染

### 知识点 ①：一个页面两套形态

- **是什么**：同一页面根据 `isAdmin` 显示不同标题、按钮和数据，而不是写两个页面。
- **为什么**：学生和管理员看的是同一批数据，只是操作权限不同，写一个页面省维护成本。
- **项目里怎么用**：`v-if="isAdmin"` 显示编辑/删除，`v-else` 显示「立即预约」；查询参数也随角色变。
- **易错点**：**隐藏按钮只是体验，不是安全**。就算学生用改前端的方式「找回」删除按钮，后端 `get_current_admin` 也会拦。

### 知识点 ②：前端体验 vs 后端权限

- **是什么**：前端隐藏按钮、后端拒绝请求，是两层不同的事。
- **为什么**：前端代码在浏览器里，用户可以改；所以任何权限判断最终必须落在后端。
- **项目里怎么用**：写接口统一 `Depends(get_current_admin)`，读接口用 `Depends(get_current_user)`。
- **易错点**：验证「越权」时，要直接用普通用户 Token 调管理员接口，看后端是否返回 403，而不是只在前端点按钮。

> 代码落点：[`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue)、[`fronted/src/views/equ.vue`](../../fronted/src/views/equ.vue)、[`fronted/src/utils/user.js`](../../fronted/src/utils/user.js)。

## 第 18 节：开发实验室预约功能

### 知识点 ①：Service 层统一业务规则

- **是什么**：把预约的核心业务逻辑（校验、冲突检查、落库）抽成一个 `services/reservation.py` 里的函数，普通接口和 AI 工具都调它。
- **为什么**：同一套规则只写一次，避免「普通预约」和「AI 预约」两套规则不一致，出现一个能过、一个不能过的漏洞。
- **项目里怎么用**：`create_reservation_record` 是唯一写入口。
- **易错点**：业务规则分散在多个入口，是这类系统最常见的 bug 来源。

### 知识点 ②：`with_for_update()` 行锁

- **是什么**：查询实验室时加 `FOR UPDATE`，锁住这一行，别的并发请求要等它提交。
- **为什么**：并发下「先查无冲突、再插入」会有竞态——两个请求同时查到无冲突，都插入成功。锁住实验室行，让「检查+写入」串行化。
- **项目里怎么用**：预约创建、取消、审核都用 `with_for_update()`。
- **易错点**：SQLite 测试环境会忽略 `FOR UPDATE`，但业务规则仍能验证；MySQL/InnoDB 才真正生效。

### 知识点 ③：半开区间冲突公式

- **是什么**：判断两个时间段是否冲突的公式——`旧开始 < 新结束 且 旧结束 > 新开始`。时间段是「半开区间」`[开始, 结束)`。
- **为什么**：半开区间意味着「前一单的结束时间」和「下一单的开始时间」相等时不冲突，可以无缝衔接。
- **项目里怎么用**：`Reservation.start_time < data.end_time, Reservation.end_time > data.start_time` 两个条件同时成立才算冲突。
- **易错点**：用 `<=`/`>=` 会误判「无缝衔接」为冲突；`pending` 和 `approved` 两种状态都占用时段，都要查。

### 知识点 ④：过去时间校验

- **是什么**：预约日期不能早于今天；如果就是今天，开始时间还要晚于当前时间。
- **为什么**：防止提交一个已经无法履行的预约。
- **项目里怎么用**：`create_reservation_record` 里两次判断，日期是今天时再比时间。
- **易错点**：只查日期不查时间，会放过「今天凌晨 00:00」这种已经过去的时段。

> 代码落点：[`backend/app/services/reservation.py`](../../backend/app/services/reservation.py)、[`backend/app/models/reservation.py`](../../backend/app/models/reservation.py)、[`backend/app/api/reservation.py`](../../backend/app/api/reservation.py)。

## 第 19 节：我的预约与预约审核

### 知识点 ①：状态机

- **是什么**：预约在几个固定状态间流转：`pending`（待审核）→ `approved`（通过）/ `rejected`（拒绝），pending/approved 还可 → `cancelled`（取消）。
- **为什么**：状态把「这条预约现在什么情况」说清楚，且约束「什么状态能做什么操作」。
- **项目里怎么用**：`status` 字段存字符串，取消、审核接口都先检查当前状态。
- **易错点**：已经处理过（approved/rejected/cancelled）的预约不能再审核或再取消，这些边界都要在接口里判。

### 知识点 ②：学生只看自己、管理员看全部

- **是什么**：`/reservations/mine` 用 `current_user.id` 过滤；管理员接口 `/reservations` 看全部。
- **为什么**：数据权限——学生不能看别人的预约。
- **项目里怎么用**：`mine` 接口里 `filter(Reservation.user_id == current_user.id)`，**绝不接受前端传来的 user_id**。
- **易错点**：前端可以伪造参数，所以「我是谁」必须来自鉴权后的 `current_user`，不能来自请求体。

### 知识点 ③：审核前复核

- **是什么**：管理员点「通过」时，后端再查一次——时间是否已过去、实验室是否仍开放。
- **为什么**：从学生提交到管理员审核之间有时间差，期间实验室可能被暂停、时间可能已经过去。
- **项目里怎么用**：`review_reservation` 里在 `approved` 分支复核时间和实验室状态。
- **易错点**：只在提交时校验、审核时不复核，会批准一个已经无法履行的预约。

### 知识点 ④：取消与审核锁同一行

- **是什么**：取消和审核都 `with_for_update()` 锁住同一条预约记录。
- **为什么**：防止学生取消和管理员审核同时读到一个 `pending`，结果互相覆盖。
- **项目里怎么用**：两个接口都先锁行，再判状态、再改。

> 代码落点：[`backend/app/api/reservation.py`](../../backend/app/api/reservation.py)、[`fronted/src/views/reservation.vue`](../../fronted/src/views/reservation.vue)。

# 第四部分：AI 助手、RAG、Agent 与 SSE

## 第 20 节：开发实验室 AI 助手对话（后端部分）

### 知识点 ①：`Literal` 限定历史角色

- **是什么**：`role: Literal["user", "assistant"]` 让字段只能取这两个值。
- **为什么**：防止客户端伪造 `system` 或 `developer` 角色的消息，注入高优先级指令操控模型。
- **项目里怎么用**：`ChatMessage.role` 用 `Literal`。
- **易错点**：这是「输入校验防注入」的一个具体例子，别只当类型注解看。

### 知识点 ②：`StreamingResponse` 流式响应

- **是什么**：返回 `StreamingResponse(生成器, media_type="text/event-stream")`，让响应体边生成边发送，而不是一次性返回。
- **为什么**：AI 回答要逐字显示，一次等全部生成完体验太差。
- **项目里怎么用**：`chat_stream` 返回一个生成器，逐个 `yield` 事件。
- **易错点**：加 `Cache-Control: no-cache` 和 `X-Accel-Buffering: no` 两个头，防止中间层（如 nginx）把流缓冲住，导致前端收不到逐条数据。

### 知识点 ③：SSE 帧格式

- **是什么**：Server-Sent Events，每条消息由 `event: 名称` + `data: JSON` 组成，以空行结尾。
- **为什么**：前端能按「事件名」分流处理（status/token/done 等）。
- **项目里怎么用**：`sse_event` 拼出 `event: {name}\ndata: {json}\n\n`。
- **易错点**：`json.dumps(..., ensure_ascii=False)` 让中文不被转成 `\u` 转义，前端更好读。

### 知识点 ④：生成器内自己管理数据库会话

- **是什么**：流式生成器内部用 `SessionLocal()` 自己开会话，`finally` 里关闭，而不是用 `Depends(get_db)`。
- **为什么**：`Depends(get_db)` 的 `finally` 在**接口函数返回时**就执行了，而那时响应体还没开始迭代——会话已经被关，后面再访问数据库就报错。
- **项目里怎么用**：`generate_events` 里 `db = SessionLocal()`，最后 `db.close()`。
- **易错点**：这是流式接口特有的坑，普通 JSON 接口用 `Depends(get_db)` 没问题，流式接口不行。

### 知识点 ⑤：异常兜底不泄露堆栈

- **是什么**：生成器里 `except Exception` 只记日志，向客户端发一条通用 `error` 事件。
- **为什么**：堆栈含文件路径和实现细节，不该给浏览器。
- **项目里怎么用**：`logger.exception(...)` 写后端终端，前端只收「AI 助手暂时无法回答」。

> 代码落点：[`backend/app/schemas/ai.py`](../../backend/app/schemas/ai.py)、[`backend/app/api/ai.py`](../../backend/app/api/ai.py)。

## 第 21 节：开发实验室 AI 助手对话（前端与联调）

### 知识点 ①：SSE 必须用 `fetch` 而不是 axios

- **是什么**：流式 POST 请求用原生 `fetch`，因为它能拿到 `response.body` 这个可读流。
- **为什么**：浏览器端的 axios 不能像 fetch 那样逐块读取响应体，只能等整个响应返回，做不到「逐字显示」。
- **项目里怎么用**：`api/ai.js` 里用 `fetch` 发请求。
- **易错点**：fetch 不走 axios 的拦截器，所以 **401 要在这里单独判断**并跳登录。

### 知识点 ②：流式读取与缓冲切分

- **是什么**：`response.body.getReader()` 逐块读，`TextDecoder(stream: true)` 解码，按 `\r?\n\r?\n`（空行）切出完整的事件块。
- **为什么**：一次读到的字节可能不是完整的一条事件，可能只来半个，所以要攒在 buffer 里，等空行出现才切。
- **项目里怎么用**：`buffer += decode(...)`，`buffer.split(/\r?\n\r?\n/)`，最后一段不完整的留下，等下一块。
- **易错点**：**流结束时（`done`）还要把残余 buffer 再处理一次**，否则最后一个 token 或 done 事件会丢。

### 知识点 ③：`AbortController` 取消与状态收尾

- **是什么**：`AbortController` 能在中途取消 fetch；`finally` 里统一复位状态。
- **为什么**：用户点「停止」要能真的中断；状态复位必须由「当前请求」负责，避免旧请求清掉新请求的状态。
- **项目里怎么用**：停止按钮只调 `abort()`；`finally` 里判断「当前控制器还是我这个」才复位。
- **易错点**：停止按钮不要直接设 `sending=false`，否则旧请求没收尾前可能发起新请求，状态串扰（现在的 `stop()` 只发 `abort()`，由请求的 `finally` 统一收尾）。

### 知识点 ④：对话状态放在 Pinia store

- **是什么**：对话的 `messages`、`sending` 和 SSE 请求都放在全局 store（`fronted/src/store/chat.js`）里，组件只负责渲染。
- **为什么**：组件切走会被销毁，页面内的状态和请求都会丢；store 不随组件销毁，回答在后台继续生成，回来能看到完整内容。
- **项目里怎么用**：`useChatStore()` 暴露 `sendMessage`、`stop`、`clearMessages`；`messages` 本身是响应式的 ref，往里面 push 普通对象再改 `content` 也能触发更新。
- **易错点**：不要整份替换数组把引用丢掉；过程标签要跟着 `tool_start`/`tool_end` 一起累积。

### 知识点 ⑤：history 在插入本轮之前生成

- **是什么**：发送前先把历史消息抓出来，再往列表里加本轮的用户消息和空白助手消息。
- **为什么**：如果先加了空白助手消息再取历史，那个空白 `content` 会被当成历史发回后端，污染上下文。
- **项目里怎么用**：`const history = messages.value.slice(-10).map(...)` 在 `push` 之前执行。
- **易错点**：顺序错了不明显，但会让模型收到脏历史。

> 代码落点：[`fronted/src/api/ai.js`](../../fronted/src/api/ai.js)、[`fronted/src/views/chat.vue`](../../fronted/src/views/chat.vue)。

## 第 22 节：用 RAG 给实验室助手接入知识库

### 知识点 ①：RAG 是什么

- **是什么**：Retrieval-Augmented Generation——回答前先从知识库「检索」出相关内容，把检索结果拼进 prompt，再让模型基于它回答。
- **为什么**：模型训练时没有你项目的知识（预约规则、设备规范），RAG 把这些「外部知识」喂给它，它才能答得准。
- **项目里怎么用**：`search_documents` 检索 `knowledge/*.md`，结果拼进上下文。
- **易错点**：RAG 的「检索」和「生成」是两段，本项目里检索是本地实现的，生成才用到模型。

### 知识点 ②：文本向量化（embedding）

- **是什么**：把一段文本变成一个数字向量，语义相近的文本向量也相近。
- **为什么**：检索时算「问题向量」和「文档向量」的距离，找最近的文档，而不是简单关键词匹配。
- **项目里怎么用**：`build_local_embedding` 用「字符 + 相邻双字符」的 blake2b 哈希生成 128 维向量，再 L2 归一化。
- **易错点**：向量要**归一化**，否则文档越长向量越大，距离比较被长度主导。

### 知识点 ③：确定性本地向量（不依赖网络）

- **是什么**：用自己的哈希函数生成向量，而不是下载 OpenAI 的嵌入模型。
- **为什么**：ChromaDB 默认会下载一个英文嵌入模型，网络慢时第一次检索会卡住；本地哈希向量离线可用，适合本项目规模。
- **项目里怎么用**：`upsert(embeddings=[build_local_embedding(...)])` 显式传向量。
- **易错点**：同一段文本每次生成的向量必须**完全相同**（确定性），否则检索结果会漂移。

### 知识点 ④：内容指纹与增量同步

- **是什么**：`build_content_hash` 用 SHA-256 算文档内容指纹；`sync_collection` 按指纹判断新增/修改/删除，只同步变化的部分。
- **为什么**：不用文件修改时间判断（复制、解压会改时间但内容没变）；增量同步避免每次全量重建索引。
- **项目里怎么用**：每次检索前先 `sync_collection`，改了知识库不用重启服务。
- **易错点**：新增、修改、删除三种情况都要处理，漏掉删除会让已删的文档还留在索引里。

### 知识点 ⑤：异常降级 `simple_search`

- **是什么**：ChromaDB 检索失败时，自动切换到本地关键词计数排序。
- **为什么**：RAG 不是登录、预约这类核心业务的硬依赖，不能因为它坏了就让 AI 功能整个不可用。
- **项目里怎么用**：`search_documents` 里 `try/except`，失败记日志并返回 `simple_search` 结果。
- **易错点**：降级要记日志（带真实原因），方便排查，而不是静默吞掉异常。

> 代码落点：[`backend/app/ai/knowledge.py`](../../backend/app/ai/knowledge.py)、[`backend/app/knowledge/lab_rules.md`](../../backend/app/knowledge/lab_rules.md)、[`backend/tests/test_knowledge.py`](../../backend/tests/test_knowledge.py)。

## 第 23 节：用 Tool Calling 让助手查询实验室数据

### 知识点 ①：Function Calling 是什么

- **是什么**：把「工具」的描述（名字、参数、作用）告诉模型，模型在回答过程中决定「要不要调用某个工具」，并生成结构化的调用参数。
- **为什么**：模型本身不能查数据库，但能「请求」调用工具；由代码真正执行工具，把结果回给模型。
- **项目里怎么用**：`TOOL_SCHEMAS` 按 Chat Completions 格式定义十个工具，`run_model_tools` 逐个执行并把结果（含 `tool_start`/`tool_end` 过程）回传。
- **易错点**：模型只负责「选工具 + 填参数」，**真正的执行和校验在代码里**，不能信模型说的结果。

### 知识点 ②：`TOOL_SCHEMAS` 与 `strict` 约束

- **是什么**：用 JSON Schema 声明每个工具的参数类型、必填项；`strict: True` + `additionalProperties: False` 强制模型只能产出合规参数。
- **为什么**：约束模型输出格式，减少「参数缺字段、类型不对」这类错误。
- **项目里怎么用**：每个工具的参数 schema 都写全 `required` 和类型，并统一用 `{"type": "function", "function": {...}}` 包装。
- **易错点**：`additionalProperties: False` 不让模型塞多余字段。

### 知识点 ③：写工具不信任模型参数

- **是什么**：`create_lab_reservation` 拿到模型的参数后，重新解析、构造 `ReservationCreate`、走一遍完整校验。
- **为什么**：模型可能给出不存在的实验室 id、过去的日期、冲突的时间——这些必须由 Service 重算，不能因为「是模型说的」就放行。
- **项目里怎么用**：写工具内部调用 `create_reservation_record`（和第 18 节普通接口同一个）。
- **易错点**：这是「三道防线」的第二道——参数校验在 Service 里，模型只是入口。

### 知识点 ④：每轮最多一次写工具

- **是什么**：`run_model_tools` 里 `write_tool_handled` 标志，一轮对话里写工具只执行一次。
- **为什么**：防止模型在一次回复里重复调用创建预约，生成两条记录。
- **项目里怎么用**：`write_tool_handled = True` 后，再遇到写工具直接返回「不重复创建」。

> 代码落点：[`backend/app/ai/tools.py`](../../backend/app/ai/tools.py)、[`backend/app/ai/agent.py`](../../backend/app/ai/agent.py)、[`backend/app/services/reservation.py`](../../backend/app/services/reservation.py)。

## 第 24 节：用 LangGraph 做智能预约 Agent

### 知识点 ①：Agent 与「状态 + 节点 + 图」

- **是什么**：LangGraph 把 Agent 逻辑组织成「状态（State）+ 节点（Node）+ 边（Edge）」。节点是处理函数，边决定执行顺序。
- **为什么**：复杂流程用图表达更清晰，且能可视化、易扩展（以后加分支只是加节点）。
- **项目里怎么用**：`AgentState` 是状态，`retrieve_node`、`agent_node`、`execute_tools_node` 是节点（无 Key 时 `agent_node` 走 `local_tool_node` 本地规则），图是带条件边的循环 `retrieve → agent ⇄ tools → END`。
- **易错点**：节点是纯函数 `state -> 部分新状态`，只返回要更新的键，不要整份复制。

### 知识点 ②：`TypedDict` 定义状态

- **是什么**：`class AgentState(TypedDict, total=False)` 用类型标注描述状态里有哪些键、各是什么类型。
- **为什么**：`total=False` 表示这些键**可选**，因为节点只返回它要更新的键，不是每个节点都填满全部状态。
- **项目里怎么用**：`message`、`history`、`user_id`、`db`、`retrieved_docs`、`messages`、`final_answer` 等都是状态的键。
- **易错点**：`total=False` 是关键，否则每个节点都得返回全部键。

### 知识点 ③：`StateGraph` 四步建图

- **是什么**：`add_node` 加节点、`set_entry_point` 设入口、`add_edge` 连边、`add_conditional_edges` 按状态决定下一步、`compile()` 编译成可执行图。
- **项目里怎么用**：`build_graph` 里完成这些步骤并返回 `(编译后的图, 引擎名)`；`agent` 后面的条件边用的就是 `should_continue`。
- **易错点**：忘了 `compile()` 图不能运行；入口只能有一个。

### 知识点 ④：`ImportError` 降级

- **是什么**：`build_graph` 里 `try import langgraph except ImportError` 返回 None 和一个「顺序编排」的说明。
- **为什么**：langgraph 是可选依赖，没装也要能跑，降级成手动按顺序调 `retrieve_node` 和 `local_tool_node`；模型调用仍由 `run_model_tools`/`stream_answer` 承担。
- **项目里怎么用**：`run_graph` 里「有图用图，没图手动调」。
- **易错点**：降级分支的执行顺序要和图里的边一致，否则行为不同。

### 知识点 ⑤：意图识别不能用「包含判断」

- **是什么**：判断用户是否「明确要预约」，用 `re.fullmatch` / `re.match` 匹配消息开头，而不是 `"帮我预约" in message`。
- **为什么**：包含判断会把「**不要**帮我预约」也判成要预约——因为字符串里确实包含了「帮我预约」。
- **项目里怎么用**：`has_explicit_reservation_intent` 用正则锚定开头；`has_cancel_reservation_intent` 识别撤回表达。
- **易错点**：这是「否定句」处理的反例，写工具前的服务端确认规则，不能只靠模型判断。

> 代码落点：[`backend/app/ai/agent.py`](../../backend/app/ai/agent.py)。

## 第 25 节：用 SSE 流式输出并让过程可见

### 知识点 ①：七种事件的职责

- **是什么**：`status`（阶段进展）、`tool_start`/`tool_end`（每个模型工具的开始/完成）、`tool`（调用了什么工具）、`token`（逐段文本）、`done`（结束）、`error`（失败）。
- **为什么**：让「过程可见」——用户能看到正在检索、调用了什么工具，而不只是等最终答案。
- **项目里怎么用**：`chat_stream` 按顺序发 `status → status →（tool_start → tool_end）→ tool → token → done`。
- **易错点**：`tool` 事件在「没调用工具」时不该发；事件顺序要稳定，前端才好处理。

### 知识点 ②：逐 token 生成

- **是什么**：`stream_answer` 有 Key 时调 Chat Completions `stream=True`，遍历 `chunk.choices[0].delta.content` 逐段 `yield`；没 Key 时把本地答案按 12 字符切片模拟流式。
- **为什么**：前端统一按「收到一段就追加一段」处理，无论有没有 Key，体验一致。
- **项目里怎么用**：无 Key 分支也 `yield`，让前端逻辑不用区分两种情况。
- **易错点**：本地答案也要走 `yield` 切片，别 `return` 一整段，否则前端收不到逐段。

### 知识点 ③：上下文分区

- **是什么**：`build_prompt_context` 把「知识库内容」和「系统实时数据/工具结果」分两个标题拼进 prompt。
- **为什么**：让模型分清「这是文档里说的规则」和「这是实时查到的数据」，避免把两者混淆。
- **项目里怎么用**：系统提示明确要求「不得编造实验室、设备或预约状态」。

> 代码落点：[`backend/app/api/ai.py`](../../backend/app/api/ai.py)、[`backend/app/ai/agent.py`](../../backend/app/ai/agent.py)。

## 第 26 节：完善系统首页与课程收尾

### 知识点 ①：聚合查询 `func.count` / `func.coalesce`

- **是什么**：SQLAlchemy 的聚合函数，`func.count` 计数，`func.coalesce(func.sum(...), 0)` 求和且空值当 0。
- **为什么**：统计「开放实验室数」「设备总数」这种跨多行的结果，用聚合函数一条 SQL 搞定。
- **项目里怎么用**：`get_summary` 里四个聚合查询。
- **易错点**：`coalesce(..., 0)` 处理「一张表空着」时 `sum` 返回 NULL 的情况；`.scalar() or 0` 再兜底一次。

### 知识点 ②：按角色区分统计口径

- **是什么**：管理员看全局统计，学生只看自己的预约数。
- **为什么**：数据权限——学生的首页不该看到全站的预约数据。
- **项目里怎么用**：`if not current_user.is_superuser` 给预约查询加 `user_id` 过滤。
- **易错点**：给一个查询加了过滤，相关的 pending 查询也要加，漏一个就泄露数据。

### 知识点 ③：`markRaw` 避免把组件变成响应式

- **是什么**：`markRaw` 标记一个对象「不要被 Vue 变成响应式代理」。
- **为什么**：图标是组件对象，放进响应式数组会被代理，Vue 会警告「组件被做成响应式对象」，还带来无谓开销。
- **项目里怎么用**：首页统计卡片里的 `icon: markRaw(Collection)`。
- **易错点**：只有「组件对象」这类不该响应式的引用需要 `markRaw`，普通数据不需要。

> 代码落点：[`backend/app/api/stats.py`](../../backend/app/api/stats.py)、[`fronted/src/views/home.vue`](../../fronted/src/views/home.vue)、[`fronted/src/api/stats.js`](../../fronted/src/api/stats.js)。

## 第 27 节：项目图解与完整链路复盘

### 知识点 ①：一条 AI 请求走完的完整链路

- **是什么**：把前面所有知识串起来——`chat.vue 发消息 → fetch 流式请求 → /api/ai/chat/stream → 鉴权 → LangGraph 编排 → RAG 检索 + 工具调用 → Service 落库 → 流式回答 → SSE 事件 → 前端逐字渲染`。
- **为什么**：单看每节是散的，串起来才理解「系统怎么运转」。排查问题时，能按这条链定位是哪一环断了。
- **易错点**：复盘时重点标出「写操作在哪一环真正落库」——是 Service 层 `db.commit()`，不是模型、也不是前端。

### 知识点 ②：写操作的三道防线（串起来看）

- **是什么**：AI 预约写库经过三重确认：① 模型只填参数（`strict` schema 约束）② 服务端校验「当前轮明确确认」（意图识别）③ Service 重算全部业务规则（`create_reservation_record`）。
- **为什么**：任何一道都不能单独信任——模型会幻觉、意图会误判、业务规则会变化，层层兜底才安全。
- **易错点**：三道防线对应三个不同文件（`tools.py` / `agent.py` / `services/reservation.py`），复习时能对着源码说出每道在哪。

### 知识点 ③：安全边界复盘

- **是什么**：全项目安全要点汇总——密钥只在 `.env`、密码存哈希、响应不带密码、写操作层层确认、CORS 只放行本机源、上传按魔数嗅探。
- **为什么**：这些不是「加分项」，是项目能安全运行的基本盘。
- **易错点**：复盘时逐条确认自己都能说出「为什么」和「在哪实现」，说不出的回去翻对应节。

> 代码落点：全项目——入口 [`backend/app/main.py`](../../backend/app/main.py)、AI 编排 [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py)、业务规则 [`backend/app/services/reservation.py`](../../backend/app/services/reservation.py)。

---

## 复习自查清单

学完一整组后，能用「遮住详解自己说」的方式过一遍下面这些问题：

1. 一次请求从浏览器到数据库要经过哪些环节？（第 00 节）
2. 为什么密钥不能放前端 `VITE_` 变量？（第 01 节）
3. 路由守卫要处理哪两个方向？（第 02 节）
4. `reactive` 和 `ref` 什么时候用哪个？共享状态靠什么实现？（第 03 节）
5. `get_db` 为什么要 `try/finally`？（第 04 节）
6. 为什么数据库存 bcrypt 哈希而不是明文？（第 05 节）
7. 改密后旧 Token 为什么自动失效？401 和 403 有什么区别？（第 06 节）
8. 为什么异常处理器不能把堆栈返回给前端？（第 07 节）
9. axios 响应拦截器处理哪三类错误？（第 08 节）
10. `model_fields_set` 解决什么问题？（第 09 节）
11. 上传为什么按魔数判断类型、为什么用 UUID 命名？（第 10 节）
12. `exclude_unset=True` 和 `joinedload` 各解决什么？（第 11 节）
13. 改密为什么要校验旧密码？（第 12 节）
14. 分页为什么要同时返回总数？（第 13 节）
15. 删除确认框的「取消」为什么要 catch？（第 14 节）
16. `only_open` 为什么只是查询选项不是权限？（第 15 节）
17. `joinedload` 解决什么性能问题？（第 16 节）
18. 为什么隐藏按钮不等于权限控制？（第 17 节）
19. 半开区间冲突公式是什么？为什么「结束等于下一单开始」不冲突？（第 18 节）
20. 审核前为什么要复核时间和实验室状态？（第 19 节）
21. 流式接口的 db 为什么不能在生成器外创建？（第 20 节）
22. SSE 为什么用 fetch 不用 axios？对话状态为什么放在 Pinia store？（第 21 节）
23. 本地向量怎么生成？为什么用内容指纹而不是文件时间？（第 22 节）
24. 写工具为什么不信任模型参数？（第 23 节）
25. 意图识别为什么不能用「包含判断」？（第 24 节）
26. 七种 SSE 事件各负责什么？（第 25 节）
27. `coalesce` 和 `markRaw` 各解决什么？（第 26 节）
28. 写操作的三道防线分别在哪三层？（第 27 节）
