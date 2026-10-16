# 智能实验室预约系统：知识点与项目代码同步学习版

这份文档解决一个明确问题：**不再先讲一页概念，再让你去另一份文档找代码。**下面每个知识点后面紧跟当前项目里真正实现它的代码、代码解释、复现位置和验证方法。

使用方式：按第 00–27 节顺序学习；先理解“为什么”，然后把代码块和链接中的完整文件对照着敲。代码块是从当前项目提取的相关完整类、函数或连续逻辑；若省略 import、CSS 或与本知识点无关的模板，会明确注明。完整文件仍以链接中的源码为准。前端目录按项目现状写作 `fronted`。

> 这不是课程视频的逐字稿，也不是每节课结束时的历史快照，而是使用**当前最终代码**重建出的可复现学习路径。真实密钥只放在本机 `backend/.env`，不要粘贴进文档、前端或聊天记录。

## 第 00 节：先看懂一次请求怎样穿过整个项目

### 知识点：前后端分层与职责边界

Vue 负责界面和交互，FastAPI 负责鉴权与业务规则，SQLAlchemy 负责数据库操作。前端隐藏按钮只能改善体验，不能代替后端权限校验。

对应项目代码：[`backend/app/main.py`](../../backend/app/main.py) 把所有业务路由接入 FastAPI；[`fronted/src/main.js`](../../fronted/src/main.js) 把路由和 Element Plus 接入 Vue。

```python
# backend/app/main.py
app = FastAPI()
app.include_router(api)

@app.get("/")
def root():
    return {"message": "FastAPI工程正在运行中"}
```

```js
// fronted/src/main.js
const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

代码如何工作：

1. 浏览器先加载 Vue，`mount('#app')` 把根组件挂到 `index.html`。
2. 页面通过 `src/api` 发 HTTP 请求。
3. FastAPI 先匹配 `app.include_router(api)` 接入的路由，再执行鉴权、校验和数据库逻辑。
4. 所以“页面能打开”只证明前端启动了；`/docs` 能打开才证明 FastAPI 启动了。

复现检查：打开 [`backend/app/api/__init__.py`](../../backend/app/api/__init__.py)，从 `prefix="/api"` 找到 `user_router`，再追到 `/api/user/info`，完整说出“页面 → axios → 路由 → 鉴权 → ORM → 响应”的顺序。

## 第 01 节：项目环境、依赖和配置

### 知识点：npm scripts、Vite 别名与 Python 虚拟环境

`package.json` 记录前端命令和依赖；Vite 的 `@` 别名代表 `fronted/src`；Python 虚拟环境避免后端依赖污染全局环境。

对应项目代码：[`fronted/package.json`](../../fronted/package.json) 和 [`fronted/vite.config.js`](../../fronted/vite.config.js)。

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.20.0",
    "element-plus": "^2.14.5",
    "vue": "^3.5.40",
    "vue-router": "^5.2.0"
  }
}
```

```js
// fronted/vite.config.js：@/api/auth 实际指向 fronted/src/api/auth
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
```

### 知识点：前后端环境变量不能混放

后端配置类从 `backend/.env` 读取数据库、JWT 和模型密钥；前端 `VITE_` 变量会进入浏览器产物，所以只能放公开的 API 地址。

```python
# backend/app/config.py
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_EXPIRE_HOURS: int
    JWT_ALGORITHM: str = "HS256"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

代码如何工作：`BaseSettings` 按字段名读取环境变量；`ENV_FILE` 使用绝对定位，因此无论终端在哪个目录启动，都读取 `backend/.env`。不要把真实配置复制进学习笔记。

复现检查：分别启动前后端，确认 Vite 页面和 `http://127.0.0.1:8000/docs` 都能打开；再故意临时写错数据库名，观察错误发生在配置读取、连接创建还是接口执行阶段。

复现命令：

```powershell
cd 'F:\fastapi项目实战\lab_agent\fronted'
npm install
npm run dev

cd '..\backend'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-all.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## 第 02 节：Vue 入口、路由和后台布局

### 知识点：嵌套路由让公共布局只写一次

父路由显示顶栏和侧栏，子路由通过 `<router-view>` 切换业务页面；登录页在布局外，因此不会显示后台菜单。

对应项目代码：[`fronted/src/router/index.js`](../../fronted/src/router/index.js)。

```js
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Layout',
      component: () => import('@/layouts/layouts.vue'),
      redirect: '/home',
      meta: { requiresAuth: true },
      children: [
        { path: 'home', name: 'Home', component: () => import('@/views/home.vue') },
        { path: 'lab', name: 'Lab', component: () => import('@/views/lab.vue') },
        { path: 'equ', name: 'Equ', component: () => import('@/views/equ.vue') },
        { path: 'user', name: 'User', component: () => import('@/views/user.vue') },
        { path: 'reservation', name: 'Reservation', component: () => import('@/views/reservation.vue') },
        { path: 'chat', name: 'Chat', component: () => import('@/views/chat.vue') }
      ]
    },
    { path: '/login', name: 'Login', component: () => import('@/views/login.vue') },
    { path: '/register', name: 'Register', component: () => import('@/views/register.vue') }
  ]
})
```

### 知识点：路由守卫只负责页面级体验

```js
router.beforeEach((to) => {
  const token = getToken()
  if (to.meta.requiresAuth && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if ((to.path === '/login' || to.path === '/register') && token) {
    return '/home'
  }
})
```

逐句理解：`requiresAuth` 标记受保护页面；没有 Token 时保存原目标地址；登录成功后可跳回。用户可以手工修改浏览器数据，所以真正安全仍依赖后端 `get_current_user/get_current_admin`。

复现检查：访问 `/lab` 时清除 Token，预期跳到 `/login?redirect=/lab`；登录后应回到原页面。

## 第 03 节：Vue 登录表单

### 知识点：`reactive`、`ref`、表单校验与 `try/finally`

表单对象适合 `reactive`，单个加载状态和组件引用适合 `ref`。提交前执行 Element Plus 校验，`finally` 保证请求成功或失败都恢复按钮。

对应项目代码：[`fronted/src/views/login.vue`](../../fronted/src/views/login.vue) 的完整登录逻辑。

```js
const route = useRoute()
const router = useRouter()
const { saveLoginData } = useUser()
const loginFormRef = ref(null)
const loadingValue = ref(false)

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, whitespace: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const login = async () => {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid || loadingValue.value) return

  loadingValue.value = true
  try {
    const res = await loginApi({
      username: form.username.trim(),
      password: form.password
    })
    saveLoginData(res.data)
    ElMessage.success('登录成功')
    const redirectPath = typeof route.query.redirect === 'string'
      ? route.query.redirect
      : '/home'
    await router.replace(redirectPath)
  } finally {
    loadingValue.value = false
  }
}
```

代码如何工作：`validate()` 失败时不发请求；`loadingValue` 同时防止重复点击；用户名可以去两端空格，密码不能随便 `trim()`；响应拦截器已经返回统一响应体，所以这里的 `res.data` 就是登录业务数据。

复现检查：分别提交空表单、错误密码和正确账号；在 Network 中确认只有通过前端校验时才出现 POST 请求。

## 第 04 节：FastAPI、数据库依赖与 CORS

### 知识点：请求级数据库 Session

每个请求创建一个 SQLAlchemy Session，请求结束无论成功还是异常都关闭。

对应项目代码：[`backend/app/database.py`](../../backend/app/database.py)。

```python
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`yield` 前是进入请求时的准备，`finally` 是请求收尾。接口写 `db: Session = Depends(get_db)` 就能复用这一生命周期。

### 知识点：CORS 与路由挂载

```python
# backend/app/main.py
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api)
```

代码如何工作：浏览器认为 5173 与 8000 是不同源，后端必须显式放行前端 Origin。ApiPost 不受浏览器 CORS 限制，所以“ApiPost 能调、浏览器不能调”通常优先检查 CORS。

复现检查：启动后端访问 `/` 和 `/docs`。`Base.metadata.create_all()` 只能建尚不存在的表，不能替代数据库迁移，也不能替你创建 MySQL 数据库本身。

## 第 05 节：登录 API、Pydantic 与密码哈希

### 知识点：输入模型、密码验证和账号枚举防护

请求模型约束输入；数据库只保存 bcrypt 哈希；“用户不存在”和“密码错误”返回同一句话，避免攻击者枚举账号。

对应项目代码：[`backend/app/api/auth.py`](../../backend/app/api/auth.py)、[`backend/app/utils/password.py`](../../backend/app/utils/password.py)。

```python
# backend/app/utils/password.py
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
```

```python
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password):
        raise BusinessException(code=BizCode.UNAUTHORIZED, message="账号或密码错误")
    if not user.is_active:
        raise BusinessException(code=BizCode.FORBIDDEN, message="账号被禁用")

    token = create_access_token(user.id, user.password)
    return Response.success(
        message="登录成功",
        data=LoginResponse(token=token, user=UserResponse.model_validate(user)),
    )
```

逐句理解：先按唯一用户名查用户；`not user or ...` 合并两类凭证错误；账号存在但被禁用是 403；只有全部通过才签发 JWT。`UserResponse` 没有密码字段，因此哈希也不会回传。

复现检查：用 ApiPost 分别测试不存在账号、错误密码、禁用账号和正确账号，预期分别为 401、401、403、200。

## 第 06 节：JWT、Bearer 鉴权与管理员权限

### 知识点：JWT 签发和密码版本指纹

JWT 的 payload 可被读到，只能放用户标识、过期时间等非秘密信息。项目额外放入密码哈希的 SHA-256 指纹：改密后数据库哈希改变，旧 Token 自动失效。

对应项目代码：[`backend/app/utils/jwt.py`](../../backend/app/utils/jwt.py)。

```python
def build_password_version(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()

def create_access_token(user_id: int, password_hash: str) -> str:
    expire = datetime.now() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "user_id": user_id,
        "password_version": build_password_version(password_hash),
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

### 知识点：依赖注入统一验证当前用户

```python
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户被禁用",
        )

    if not hmac.compare_digest(
        payload.get("password_version", ""),
        build_password_version(user.password),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码已修改，请重新登录",
        )
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise BusinessException(code=BizCode.FORBIDDEN, message="当前账号没有管理权限")
    return current_user
```

这里把两个源码文件的相关函数放在一起便于学习。401 表示凭证无效；403 表示身份已确认但角色不允许。完整实现分别见 [`auth.py`](../../backend/app/dependencies/auth.py) 和 [`permission.py`](../../backend/app/dependencies/permission.py)。

复现检查：登录后用 Bearer Token 调 `/api/user/info`；改密后再用旧 Token 请求，应返回 401。

## 第 07 节：统一响应与全局异常处理

### 知识点：统一 JSON 结构与真实 HTTP 状态码

项目响应体统一为 `code/message/data`，但错误仍返回真实 4xx/5xx，方便浏览器、ApiPost 和监控正确判断失败。

对应项目代码：[`backend/app/common/response.py`](../../backend/app/common/response.py)。

```python
class Response(BaseModel):
    code: int
    message: str
    data: Any = None

    @classmethod
    def success(cls, message: str = "请求成功", data: Any = None):
        return cls(code=BizCode.SUCCESS, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "请求失败"):
        return cls(code=code, message=message)
```

### 知识点：业务、HTTP、参数与未知异常分开处理

```python
async def business_exception_handler(request: Request, exc: BusinessException):
    logger.warning(f"业务异常 | 路径:{request.url.path} | 错误:{exc.message}")
    code = int(exc.code)
    http_status = code if 400 <= code <= 599 else int(BizCode.INTERNAL_ERROR)
    return JSONResponse(
        status_code=http_status,
        content=Response.error(code=exc.code, message=exc.message).model_dump(),
    )

async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未捕获异常 | 路径:{request.url.path}")
    return JSONResponse(
        status_code=int(BizCode.INTERNAL_ERROR),
        content=Response.error(
            code=BizCode.INTERNAL_ERROR,
            message="服务器开小差了，请稍后重试",
        ).model_dump(),
    )
```

逐句理解：已预见的业务错误给用户明确提示；未知异常用 `logger.exception` 记录堆栈，对外只给通用文案，避免泄露服务器路径和实现细节。参数异常的完整提取逻辑见 [`exceptions.py`](../../backend/app/common/exceptions.py)。

复现检查：缺少必填字段触发参数异常，错误登录触发业务异常；比较 HTTP 状态码和统一响应体。

## 第 08 节：axios 封装与前后端联调

### 知识点：请求拦截、响应解包与统一错误处理

对应项目代码：[`fronted/src/utils/request.js`](../../fronted/src/utils/request.js)。

```js
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 30000
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code === 200) return data
    ElMessage.error(data.message || '请求失败')
    if (data.code === 401) {
      logout()
      router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    }
    return Promise.reject(data)
  },
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.message
    if (status === 401) {
      logout()
      router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else if (!error.response) {
      ElMessage.error('网络异常，请检查后端服务是否启动')
    } else {
      ElMessage.error(message || '请求失败')
    }
    return Promise.reject(error)
  }
)
```

代码如何工作：请求拦截器让业务页面不用重复添加 Token；成功拦截器返回的是 `response.data`，所以页面拿到的 `res.data` 是统一响应中的业务数据；失败拦截器区分登录失效、超时、服务器错误和后端未启动。

复现检查：登录后看 Network 请求头；停掉 FastAPI 再加载列表，应该显示网络异常；重新启动后恢复。

## 第 09 节：用户注册

### 知识点：前后端双重校验、密码哈希和数据库唯一约束

前端校验改善体验，但可以被绕过；Pydantic 和数据库约束才是后端边界。公开注册接口必须固定创建普通用户，不能从请求体读取管理员角色。

对应项目代码：[`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) 的输入模型。

```python
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=64)
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("用户名至少需要 3 个非空白字符")
        return cleaned
```

这段解决了 `Field(min_length=3)` 仍可能接受三个空格的问题：自定义校验器先 `strip()`，然后再按非空白字符判断，并且必须返回处理后的值。

对应项目代码：[`backend/app/api/auth.py`](../../backend/app/api/auth.py) 的完整注册函数。

```python
@router.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    username = data.username.strip()
    full_name = data.full_name.strip() if data.full_name else None

    if db.query(User).filter(User.username == username).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="用户名已存在")
    if db.query(User).filter(User.email == data.email).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="邮箱已被注册")

    user = User(
        username=username,
        password=hash_password(data.password),
        email=str(data.email).lower(),
        full_name=full_name,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise BusinessException(code=BizCode.BAD_REQUEST, message="用户名或邮箱已存在")

    return Response.success(
        message="注册成功",
        data=UserResponse.model_validate(user),
    )
```

逐句理解：预查询负责友好提示；数据库 `unique` 负责并发情况下的最终保证；异常后必须 `rollback()`；`is_superuser=False` 阻止公开注册自我提权。

前端 [`register.vue`](../../fronted/src/views/register.vue) 只提交后端真正需要的四个字段，“确认密码”只参与页面校验：

```js
const handleRegister = async () => {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid || loadingValue.value) return
  loadingValue.value = true
  try {
    await registerApi({
      username: registerForm.username.trim(),
      email: registerForm.email.trim(),
      full_name: registerForm.full_name.trim() || null,
      password: registerForm.password
    })
    ElMessage.success('注册成功，请使用新账号登录')
    await router.replace('/login')
  } finally {
    loadingValue.value = false
  }
}
```

复现检查：测试全空格用户名、短密码、错误邮箱、重复邮箱和正常注册；确认响应永远不包含密码字段。

## 第 10 节：图片上传 API

### 知识点：`multipart/form-data`、有界读取、文件魔数和安全文件名

浏览器使用 `FormData` 上传二进制文件；后端不能只相信文件名和 MIME，而要限制读取大小并检查真实文件头。随机 UUID 防止重名和路径穿越。

对应项目代码（前端）：[`fronted/src/api/user.js`](../../fronted/src/api/user.js)。

```js
export function uploadImageApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/upload/image', formData)
}
```

对应项目代码（后端类型识别）：[`backend/app/api/upload.py`](../../backend/app/api/upload.py)。

```python
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024

def detect_image_suffix(content: bytes) -> str | None:
    if (
        content.startswith(b"\x89PNG\r\n\x1a\n")
        and content[12:16] == b"IHDR"
        and b"IEND" in content[-24:]
    ):
        return ".png"
    if content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9"):
        return ".jpg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None
```

完整上传函数：

```python
@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    declared_suffix = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not declared_suffix:
        raise BusinessException(code=400, message="只支持 JPG、PNG、WEBP 图片")

    content = await file.read(MAX_IMAGE_SIZE + 1)
    await file.close()
    if len(content) > MAX_IMAGE_SIZE:
        raise BusinessException(code=400, message="图片大小不能超过 5MB")

    detected_suffix = detect_image_suffix(content)
    if not detected_suffix or detected_suffix != declared_suffix:
        raise BusinessException(code=400, message="图片内容与文件类型不匹配")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{detected_suffix}"
    (UPLOAD_DIR / filename).write_bytes(content)
    return Response.success(
        message="上传成功",
        data={"filename": filename, "url": f"/uploads/{filename}"},
    )
```

代码如何工作：最多读取 `5MB + 1`，多出的一个字节用来判断超限；声明类型与文件内容必须一致；最终只用后端生成的文件名。`main.py` 把上传目录挂载到 `/uploads`，浏览器才能预览。

复现检查：上传真实图片、超过 5MB 的图片、把文本改名为 `.png` 的伪图片。当前功能**只是上传并预览 URL，没有把 URL 保存成用户头像字段**。

## 第 11 节：修改个人资料

### 知识点：当前用户来自 JWT，不能相信请求体中的用户 ID

用户修改的是“自己的”资料，所以接口根本不接收 `user_id`；`get_current_user` 从 JWT 找到目标用户。邮箱查重要排除当前用户自己。

对应项目代码：[`backend/app/api/user.py`](../../backend/app/api/user.py)。

```python
@router.put("/profile")
def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email = str(data.email).lower()
    email_owner = db.query(User).filter(
        User.email == email,
        User.id != current_user.id,
    ).first()
    if email_owner:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="邮箱已被其他账号使用")

    current_user.email = email
    current_user.full_name = data.full_name.strip() if data.full_name else None
    db.commit()
    db.refresh(current_user)
    return Response.success(
        message="个人信息修改成功",
        data=UserResponse.model_validate(current_user),
    )
```

### 知识点：保存后同步模块级共享状态

[`fronted/src/utils/user.js`](../../fronted/src/utils/user.js) 把 `userInfo` 放在 `useUser()` 外面，因此所有组件共享同一个 `ref`。

```js
const userInfo = ref(getUserInfo())

export function useUser() {
  const isAdmin = computed(() => Boolean(userInfo.value?.is_superuser))

  function updateUser(user) {
    setUserInfo(user)
    userInfo.value = user
  }
  return { userInfo, isAdmin, updateUser /* 其余方法见完整文件 */ }
}
```

页面保存函数：

```js
const saveProfile = async () => {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const res = await updateProfileApi({
      email: profileForm.email.trim(),
      full_name: profileForm.full_name.trim() || null
    })
    updateUser(res.data)
    ElMessage.success('个人信息修改成功')
  } finally {
    savingValue.value = false
  }
}
```

复现检查：改成自己原邮箱应成功，改成其他用户邮箱应失败；保存成功后不用刷新，顶栏姓名也应同步变化。

## 第 12 节：修改密码与旧 Token 失效

### 知识点：敏感操作再次验证旧密码

只有 Token 不足以执行改密，因为 Token 可能被盗；后端还要求用户证明知道旧密码，并禁止新旧密码相同。

对应项目代码：[`backend/app/api/user.py`](../../backend/app/api/user.py) 的 `update_password`，以及 [`backend/app/utils/jwt.py`](../../backend/app/utils/jwt.py) 的密码版本指纹。

```python
@router.put("/password")
def update_password(
    data: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.password):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="原密码不正确")
    if data.old_password == data.new_password:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="新密码不能与原密码相同")

    current_user.password = hash_password(data.new_password)
    db.commit()
    return Response.success(message="密码修改成功，请重新登录")
```

前端成功后清理本地凭证：

```js
const savePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await updatePasswordApi({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    clearLoginData()
    await router.replace('/login')
  } finally {
    savingValue.value = false
  }
}
```

代码如何工作：前端主动退出是良好体验；即使攻击者不走前端，旧 Token 的 `password_version` 与新密码哈希也不一致，后端会拒绝。

复现检查：用错误旧密码改密应失败；成功后旧 Token 调 `/api/user/info` 应返回 401。

## 第 13 节：管理员用户列表与分页

### 知识点：查询参数、模糊搜索、`count/offset/limit`

对应项目代码：[`backend/app/api/user.py`](../../backend/app/api/user.py) 的完整列表函数。

```python
@router.get("")
def get_user_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if keyword.strip():
        search_value = f"%{keyword.strip()}%"
        query = query.filter(or_(
            User.username.like(search_value),
            User.full_name.like(search_value),
            User.email.like(search_value),
        ))

    total = query.count()
    users = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Response.success(data={
        "list": [UserResponse.model_validate(user) for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    })
```

逐句理解：`Query` 限制页码范围；搜索条件加在 `count()` 之前，因此总数与列表使用同一过滤；第 1 页偏移 0，第 2 页偏移 `page_size`；管理员依赖防止普通用户读取全部用户。

前端把分页器与请求参数绑定：

```js
const searchParams = reactive({ page: 1, page_size: 10, keyword: '' })
const userList = ref([])
const userTotal = ref(0)

const loadUserList = async () => {
  loadingValue.value = true
  try {
    const res = await getUserListApi(searchParams)
    userList.value = res.data.list
    userTotal.value = res.data.total
  } finally {
    loadingValue.value = false
  }
}
```

复现检查：搜索用户名、姓名、邮箱并切页；使用学生 Token 直接请求 `/api/user` 应得到 403。

## 第 14 节：管理员新增、编辑和删除用户

### 知识点：一个弹窗复用新增/编辑，后端再保护关键操作

前端以 `userForm.id` 区分模式；编辑模式不重设用户名或密码，只修改邮箱、姓名、角色和启用状态。

对应项目代码：[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 与 [`backend/app/api/user.py`](../../backend/app/api/user.py)。

```js
const openUserDialog = (user = null) => {
  Object.assign(
    userForm,
    user
      ? { ...user, password: '' }
      : {
          id: null, username: '', password: '', full_name: '', email: '',
          is_active: true, is_superuser: false
        }
  )
  userDialogVisible.value = true
}

const saveUser = async () => {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    if (userForm.id) {
      await updateUserApi(userForm.id, {
        email: userForm.email.trim(),
        full_name: userForm.full_name?.trim() || null,
        is_active: userForm.is_active,
        is_superuser: userForm.is_superuser
      })
    } else {
      await createUserApi({
        username: userForm.username.trim(),
        password: userForm.password,
        email: userForm.email.trim(),
        full_name: userForm.full_name.trim() || null,
        is_active: userForm.is_active,
        is_superuser: userForm.is_superuser
      })
    }
    userDialogVisible.value = false
    await loadUserList()
  } finally {
    savingValue.value = false
  }
}
```

后端更新使用 `exclude_unset=True`，并阻止管理员禁用或降权自己：

```python
@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise BusinessException(code=BizCode.NOT_FOUND, message="用户不存在")
    if user.id == current_admin.id and data.is_active is False:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="不能禁用当前登录账号")
    if user.id == current_admin.id and data.is_superuser is False:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="不能取消自己的管理员权限")

    update_data = data.model_dump(exclude_unset=True)
    if "email" in update_data:
        update_data["email"] = str(update_data["email"]).lower()
        exists = (
            db.query(User)
            .filter(User.email == update_data["email"], User.id != user_id)
            .first()
        )
        if exists:
            raise BusinessException(
                code=BizCode.BAD_REQUEST,
                message="邮箱已被其他账号使用",
            )
    if update_data.get("full_name"):
        update_data["full_name"] = update_data["full_name"].strip()

    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return Response.success(message="用户修改成功", data=UserResponse.model_validate(user))
```

逐段理解：先查目标用户并保护当前管理员；`exclude_unset=True` 只修改请求明确传入的字段；邮箱先统一为小写再排除当前用户查重；最后才用 `setattr` 批量赋值并提交。删除前端还要 `await ElMessageBox.confirm()`；用户取消会让 Promise reject，应该 `catch` 后直接返回。后端仍必须阻止删除自己，并在外键冲突时 `rollback()`。

复现检查：新增普通用户、修改角色、尝试禁用自己、取消删除确认、删除已有预约的用户；分别观察前端与后端承担的保护。

## 第 15 节：实验室管理

### 知识点：一张业务表如何经过 ORM、Schema、路由和 Vue

ORM 描述数据库字段，Pydantic Schema 描述接口输入/输出，路由执行业务，Vue 页面调用接口。三者不能混成一个类。

对应项目代码（数据库模型）：[`backend/app/models/lab.py`](../../backend/app/models/lab.py)。

```python
class Lab(Base):
    __tablename__ = "labs"
    __table_args__ = {"comment": "实验室表"}

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(default=1, nullable=False)
```

列表与创建接口：[`backend/app/api/lab.py`](../../backend/app/api/lab.py)。

```python
@router.get("")
def get_lab_list(
    keyword: str = "",
    only_open: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Lab)
    if keyword.strip():
        query = query.filter(Lab.name.like(f"%{keyword.strip()}%"))
    if only_open:
        query = query.filter(Lab.status == 1)
    labs = query.order_by(Lab.id.desc()).all()
    return Response.success(data=[LabResponse.model_validate(lab) for lab in labs])

@router.post("")
def create_lab(
    data: LabCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if db.query(Lab).filter(Lab.name == data.name.strip()).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室名称已存在")
    lab = Lab(**data.model_dump())
    lab.name = lab.name.strip()
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return Response.success(message="实验室新增成功", data=LabResponse.model_validate(lab))
```

代码如何工作：查询只要求登录；创建、修改、删除要求管理员；`only_open` 只是查询过滤选项，不是权限规则。`status=0` 表示暂停开放。有关联设备或预约时删除可能被外键阻止，此时应改为暂停而不是强删。

前端保存时同一个弹窗复用新增和修改：

```js
const saveLab = async () => {
  const valid = await labFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = {
      name: labForm.name.trim(),
      location: labForm.location.trim(),
      capacity: labForm.capacity,
      description: labForm.description || null,
      status: labForm.status
    }
    if (labForm.id) await updateLabApi(labForm.id, data)
    else await createLabApi(data)
    labDialogVisible.value = false
    await loadLabList()
  } finally {
    savingValue.value = false
  }
}
```

复现检查：新增实验室、修改容量、暂停开放，再用学生账号观察列表过滤；普通用户直接 POST `/api/labs` 应返回 403。

## 第 16 节：实验室设备管理

### 知识点：外键、关系加载和 N+1 查询

设备的 `lab_id` 是外键，`relationship` 让 Python 对象能访问所属实验室。列表使用 `joinedload` 一次带出关联实验室，避免每行额外查询一次。

对应项目代码（数据库模型）：[`backend/app/models/equipment.py`](../../backend/app/models/equipment.py)。

```python
class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = {"comment": "实验室设备表"}

    lab_id: Mapped[int] = mapped_column(
        ForeignKey("labs.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(default=1, nullable=False)

    lab = relationship("Lab")
```

设备列表：[`backend/app/api/equipment.py`](../../backend/app/api/equipment.py)。

```python
def equipment_to_dict(equipment: Equipment) -> dict:
    return {
        "id": equipment.id,
        "lab_id": equipment.lab_id,
        "lab_name": equipment.lab.name if equipment.lab else None,
        "name": equipment.name,
        "code": equipment.code,
        "quantity": equipment.quantity,
        "description": equipment.description,
        "status": equipment.status,
        "create_time": equipment.create_time,
        "update_time": equipment.update_time,
    }

@router.get("")
def get_equipment_list(
    lab_id: int | None = None,
    keyword: str = "",
    only_available: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Equipment).options(joinedload(Equipment.lab))
    if lab_id:
        query = query.filter(Equipment.lab_id == lab_id)
    if keyword.strip():
        query = query.filter(Equipment.name.like(f"%{keyword.strip()}%"))
    if only_available:
        query = query.filter(Equipment.status == 1, Equipment.quantity > 0)
    items = query.order_by(Equipment.id.desc()).all()
    return Response.success(data=[equipment_to_dict(item) for item in items])
```

逐句理解：`joinedload(Equipment.lab)` 提前加载关系；`equipment_to_dict` 给前端直接提供 `lab_name`；`only_available` 只检查设备自己的状态和数量，**当前代码不会进一步检查所属实验室是否开放**。

复现检查：创建重复设备编号应失败；数量改为 0 后学生默认列表不显示；按 `lab_id` 筛选并观察返回的 `lab_name`。

## 第 17 节：学生端和管理端共用页面

### 知识点：角色派生状态和条件渲染

同一个页面根据 `isAdmin` 显示不同标题、按钮和过滤条件，减少重复组件。权限安全仍由后端依赖保证。

对应项目代码（共享角色状态）：[`fronted/src/utils/user.js`](../../fronted/src/utils/user.js)；页面渲染见 [`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue)；后端权限见 [`backend/app/dependencies/permission.py`](../../backend/app/dependencies/permission.py)。

```js
// fronted/src/utils/user.js
const userInfo = ref(getUserInfo())

export function useUser() {
  const isAdmin = computed(() => Boolean(userInfo.value?.is_superuser))
  // 其余登录状态方法见完整文件。
  return { userInfo, isAdmin, saveLoginData, updateUser, reloadUser, clearLoginData }
}
```

实验室页面的实际用法：[`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue)。

```vue
<h1 class="page-title">{{ isAdmin ? '实验室管理' : '可预约实验室' }}</h1>
<el-button v-if="isAdmin" type="primary" @click="openLabDialog()">
  新增实验室
</el-button>
```

```js
const { isAdmin } = useUser()

const loadLabList = async () => {
  loadingValue.value = true
  try {
    const res = await getLabListApi({
      keyword: keyword.value,
      only_open: !isAdmin.value
    })
    labList.value = res.data
  } finally {
    loadingValue.value = false
  }
}

const showEquipment = (lab) => {
  router.push({ path: '/equ', query: { lab_id: lab.id } })
}
```

代码如何工作：学生查询时传 `only_open=true`，管理员看全部；点击查看设备用路由 query 把实验室 ID 带到设备页。任何人都能伪造前端状态，所以 POST/PUT/DELETE 仍必须依赖 `get_current_admin`。

复现检查：分别用学生和管理员登录，记录标题、按钮和数据差异；再用学生 Token 直接请求管理接口，确认后端返回 403。

## 第 18 节：创建实验室预约

### 知识点：跨字段校验和统一 Service 层

结束时间必须晚于开始时间，这是两个字段共同决定的规则，适合 `model_validator`。普通 REST 接口与 AI 工具都调用同一个 Service，保证规则不会漂移。

对应项目代码（请求模型）：[`backend/app/schemas/reservation.py`](../../backend/app/schemas/reservation.py)；核心业务规则在 [`backend/app/services/reservation.py`](../../backend/app/services/reservation.py)。

```python
class ReservationCreate(BaseModel):
    lab_id: int
    reservation_date: date
    start_time: time
    end_time: time
    purpose: str = Field(min_length=2, max_length=1000)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self
```

核心业务函数：[`backend/app/services/reservation.py`](../../backend/app/services/reservation.py)。

```python
def create_reservation_record(
    db: Session,
    user_id: int,
    data: ReservationCreate,
) -> Reservation:
    lab = (
        db.query(Lab)
        .filter(Lab.id == data.lab_id)
        .with_for_update()
        .first()
    )
    if not lab or lab.status != 1:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室不存在或未开放")

    now = datetime.now()
    if data.reservation_date < now.date():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="不能预约过去的日期")
    if data.reservation_date == now.date() and data.start_time <= now.time():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="预约开始时间必须晚于当前时间")

    conflict = db.query(Reservation).filter(
        Reservation.lab_id == data.lab_id,
        Reservation.reservation_date == data.reservation_date,
        Reservation.status.in_(["pending", "approved"]),
        Reservation.start_time < data.end_time,
        Reservation.end_time > data.start_time,
    ).first()
    if conflict:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="该时间段已有预约，请选择其他时间")

    reservation = Reservation(user_id=user_id, status="pending", **data.model_dump())
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="预约创建失败，请确认用户和实验室信息",
        ) from exc
    db.refresh(reservation)
    return reservation
```

逐句理解：先锁定实验室行，再检查开放与时间；冲突公式是 `旧开始 < 新结束 且旧结束 > 新开始`；只有 `pending/approved` 占用时段；最后写入初始状态 `pending`。`with_for_update()` 在 MySQL/InnoDB 中串行化同一实验室的并发预约，SQLite 测试不会真正模拟这个锁。

前端提交：

```js
await createReservationApi({
  lab_id: selectedLab.value.id,
  reservation_date: reservationForm.reservation_date,
  start_time: reservationForm.timeRange[0],
  end_time: reservationForm.timeRange[1],
  purpose: reservationForm.purpose.trim()
})
await router.push('/reservation')
```

复现检查：测试过去日期、当天过去时刻、完全重叠、部分重叠，以及 `09:00–10:00` 后紧接 `10:00–11:00`。当前 UI 只给学生展示预约按钮，但后端 POST 只要求“已登录”，管理员直接调用接口也能创建，这是当前实现范围。

## 第 19 节：我的预约、取消和管理员审核

### 知识点：状态机和数据范围

预约状态为 `pending / approved / rejected / cancelled`。学生查询必须按自己的 `user_id` 过滤；管理员查询全部。取消与审核都锁定同一行，避免双方同时基于旧状态更新。

对应项目代码（学生取消与管理员审核）：[`backend/app/api/reservation.py`](../../backend/app/api/reservation.py)。

```python
@router.put("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservation = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id)
        .with_for_update()
        .first()
    )
    if not reservation or reservation.user_id != current_user.id:
        raise BusinessException(code=BizCode.NOT_FOUND, message="预约记录不存在")
    if reservation.status not in ("pending", "approved"):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="当前状态不能取消")
    reservation.status = "cancelled"
    db.commit()
    return Response.success(message="预约已取消")
```

管理员审核函数的关键完整流程：

```python
@router.put("/{reservation_id}/review")
def review_reservation(
    reservation_id: int,
    data: ReservationReview,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if data.status not in ("approved", "rejected"):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="审核状态不正确")
    reservation = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id)
        .with_for_update()
        .first()
    )
    if not reservation:
        raise BusinessException(code=BizCode.NOT_FOUND, message="预约记录不存在")
    if reservation.status != "pending":
        raise BusinessException(code=BizCode.BAD_REQUEST, message="该预约已经处理")

    if data.status == "approved":
        now = datetime.now()
        if reservation.reservation_date < now.date() or (
            reservation.reservation_date == now.date()
            and reservation.start_time <= now.time()
        ):
            raise BusinessException(code=BizCode.BAD_REQUEST, message="预约时间已经过去，不能通过审核")
        lab = db.query(Lab).filter(
            Lab.id == reservation.lab_id
        ).with_for_update().first()
        if not lab or lab.status != 1:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室当前未开放，不能通过审核")

    reservation.status = data.status
    reservation.review_comment = data.review_comment
    db.commit()
    return Response.success(message="预约审核完成")
```

代码如何工作：审核只允许待处理记录；拒绝不需要检查实验室状态；通过必须复核日期和开放状态，因为从提交到审核之间情况可能变化。学生取消与管理员审核锁同一预约行，使最终状态只有一个。

复现检查：走完“学生提交 → 管理员通过/拒绝 → 学生查看”；再测试他人取消、重复审核、暂停实验室后通过审核，预期后端都能守住规则。

## 第 20 节：AI 对话后端

### 知识点：对话输入校验、JWT 鉴权和流式响应

历史消息只允许 `user/assistant`，阻止浏览器伪造 `system` 角色；问题、单条历史和历史数量都有上限。对话也是登录后功能，所以仍要使用用户 JWT。

对应项目代码（请求模型）：[`backend/app/schemas/ai.py`](../../backend/app/schemas/ai.py)；流式路由在 [`backend/app/api/ai.py`](../../backend/app/api/ai.py)。

```python
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
```

对话路由：[`backend/app/api/ai.py`](../../backend/app/api/ai.py)。

```python
@router.post("/chat/stream")
def chat_stream(data: ChatRequest, current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    history = [item.model_dump() for item in data.history]

    def generate_events():
        db = SessionLocal()
        try:
            yield sse_event("status", {"message": f"正在通过 {GRAPH_ENGINE} 分析问题…"})
            state = run_graph(data.message, user_id, db, history)
            yield sse_event("status", {
                "message": f"已使用 {state.get('retrieval_engine', '知识库')} 完成 RAG 检索"
            })

            model_tool_results = run_model_tools(data.message, user_id, db, history)
            used_tools = state.get("used_tools", [])
            if model_tool_results:
                used_tools.append("OpenAI Tool Calling")
            if used_tools:
                yield sse_event("tool", {"message": "已调用：" + "、".join(used_tools)})

            context = build_prompt_context(state, model_tool_results)
            for token in stream_answer(data.message, history, context):
                yield sse_event("token", {"content": token})
            yield sse_event("done", {"message": "回答完成"})
        except Exception:
            logger.exception("AI 助手处理失败")
            yield sse_event("error", {"message": "AI 助手暂时无法回答，请稍后重试"})
        finally:
            db.close()

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

逐句理解：流式生成器可能在路由函数返回后继续执行，因此数据库 Session 在生成器内部创建和关闭；异常堆栈只写后端日志，对前端发送通用 `error` 事件；这个响应是 `text/event-stream`，不是普通统一 JSON。

复现检查：用 ApiPost 带用户登录 JWT 请求 `/api/ai/chat/stream`；不带 JWT 应返回 401。用户 JWT 和模型 API Key 是两种不同凭证。

## 第 21 节：AI 对话前端与流式联调

### 知识点：POST SSE 使用 `fetch`、ReadableStream 和缓冲区

原生 `EventSource` 不方便发送 JSON POST 和 Authorization；浏览器 axios 也不能像 fetch 一样逐块读取当前响应，因此项目使用 `fetch`。

对应项目代码：[`fronted/src/api/ai.js`](../../fronted/src/api/ai.js)。

```js
export async function streamChatApi(data, onEvent, signal) {
  const response = await fetch(`${apiBaseUrl}/api/ai/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`
    },
    body: JSON.stringify(data),
    signal
  })

  if (response.status === 401) {
    const redirectPath = router.currentRoute.value.fullPath
    logout()
    await router.replace({ path: '/login', query: { redirect: redirectPath } })
    throw new Error('登录已失效，请重新登录')
  }
  if (!response.ok || !response.body) throw new Error('AI 服务请求失败')

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const handleEventBlock = (block) => {
    if (!block.trim()) return
    let eventName = 'message'
    let eventData = null
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) eventName = line.slice(6).trim()
      if (line.startsWith('data:')) eventData = JSON.parse(line.slice(5).trim())
    }
    if (eventData) onEvent(eventName, eventData)
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const eventBlocks = buffer.split(/\r?\n\r?\n/)
    buffer = eventBlocks.pop() || ''
    for (const block of eventBlocks) handleEventBlock(block)
    if (done) {
      handleEventBlock(buffer)
      break
    }
  }
}
```

代码如何工作：一个网络块可能只有半条 SSE，因此先追加到 `buffer`，只解析以空行分隔的完整事件；最后还要处理残留内容。fetch 不经过 axios 拦截器，所以 401 要单独退出登录。

### 知识点：Pinia store 承载流式消息与 `AbortController`

[`fronted/src/store/chat.js`](../../fronted/src/store/chat.js) 的发送逻辑（组件只负责渲染，切页后回答仍在后台继续生成）：

```js
async function sendMessage(question) {
  if (!question || sending.value) return

  // 历史消息必须在加入本轮空白回复之前生成。
  const history = messages.value.slice(-10).map(({ role, content }) => ({ role, content }))
  addMessage({ role: 'user', content: question, events: [] })

  // 用普通对象即可，store 的 messages 本身是响应式的。
  const assistantMessage = { role: 'assistant', content: '', events: [] }
  addMessage(assistantMessage)

  sending.value = true
  const currentController = new AbortController()
  abortController = currentController

  try {
    await streamChatApi(
      { message: question, history },
      (eventName, data) => {
        if (eventName === 'token') assistantMessage.content += data.content
        if (eventName === 'status' || eventName === 'tool') assistantMessage.events.push(data.message)
        if (eventName === 'tool_start') assistantMessage.events.push('正在' + data.label + '…')
        if (eventName === 'tool_end') assistantMessage.events.push('✓ ' + data.label + '完成')
        if (eventName === 'error') assistantMessage.content = data.message
      },
      currentController.signal
    )
  } catch (error) {
    if (error.name === 'AbortError') {
      if (!assistantMessage.content) assistantMessage.content = '已停止生成。'
      assistantMessage.events.push('用户已停止回答')
    } else {
      assistantMessage.content = assistantMessage.content || 'AI 助手暂时无法回答，请稍后重试。'
    }
  } finally {
    // 只允许当前请求清理自己的状态。
    if (abortController === currentController) {
      sending.value = false
      abortController = null
    }
  }
}
```

这是从 store 的完整函数中保留流式状态主线的教学节选；完整版还包含 `stop()` 与 `clearMessages()`。`messages` 本身是响应式的 ref，回复对象用普通对象即可；旧请求只能清理自己的控制器，避免快速停止和重发时串状态。

复现检查：提问后观察 status、tool_start/tool_end、tool 和逐段回答；点击停止；切到其他页面再回来，对话和后台生成不丢失。

## 第 22 节：RAG 与 ChromaDB 知识库

### 知识点：知识加载、本地向量和索引同步

RAG 是“检索资料 + 把资料提供给回答层”。本项目把每份 Markdown 按空行分段并累积分块（每块约 200～400 字，块 ID 形如 `safety_chunk0`）；使用字符与相邻双字符的确定性哈希向量，演示离线索引，不是 OpenAI Embeddings，也没有相似度阈值。

对应项目代码（本地向量与 ChromaDB 检索）：[`backend/app/ai/knowledge.py`](../../backend/app/ai/knowledge.py)。

```python
def build_local_embedding(text: str, dimensions: int = 128) -> list[float]:
    normalized_text = "".join(text.lower().split())
    if not normalized_text:
        return [0.0] * dimensions

    tokens = list(normalized_text)
    tokens.extend(
        normalized_text[index:index + 2]
        for index in range(len(normalized_text) - 1)
    )
    vector = [0.0] * dimensions
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        vector_index = int.from_bytes(digest[:2], "big") % dimensions
        direction = 1.0 if digest[2] % 2 else -1.0
        vector[vector_index] += direction

    vector_length = math.sqrt(sum(value * value for value in vector))
    return [value / vector_length for value in vector] if vector_length else vector
```

代码如何工作：同样的 token 总会映射到同样维度；正负方向降低哈希碰撞偏差；L2 归一化避免长文档仅凭长度占优势。它能做简单相关性演示，但不真正理解语义。

查询与降级：

```python
def search_documents(query: str, limit: int = 3) -> tuple[list[dict[str, str]], str]:
    try:
        import chromadb

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_or_create_collection(name="lab_knowledge")
        documents = load_documents()
        sync_collection(collection, documents)

        document_count = collection.count()
        if document_count == 0 or limit <= 0:
            return [], "ChromaDB"

        result = collection.query(
            query_embeddings=[build_local_embedding(query)],
            n_results=min(limit, document_count),
        )
        items = []
        for text, metadata in zip(
            result.get("documents", [[]])[0],
            result.get("metadatas", [[]])[0],
        ):
            items.append({"text": text, "source": metadata.get("source", "knowledge")})
        return items, "ChromaDB"
    except Exception as exc:
        logger.warning("ChromaDB 检索失败，已切换到本地关键词检索：%s", exc)
        return simple_search(query, limit), "本地关键词检索"
```

`sync_collection()` 会比较 SHA-256 内容指纹：新增/修改用 `upsert`；本地删除的文档（以及不再存在的分块）从 collection 删除。完整实现紧邻该函数。

复现检查：运行 `python -m unittest tests.test_knowledge -v`；测试使用临时目录，不改开发知识库。再阅读 `backend/app/knowledge/*.md`，解释 Markdown、ChromaDB 和模型各负责什么。

## 第 23 节：Tool Calling 与可信业务工具

### 知识点：模型只选择工具，Python 才真正执行

工具 Schema 告诉模型函数名和参数格式；模型输出不能直接写数据库。后端解析参数、构造 Pydantic 模型并复用预约 Service。

对应项目代码（工具定义和执行）：[`backend/app/ai/tools.py`](../../backend/app/ai/tools.py)；模型工具选择在 [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py)。

```python
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_open_labs",
            "description": "查询当前开放的实验室以及可用设备",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function",
        "function": {
            "name": "create_lab_reservation",
            "description": "信息完整并得到用户明确要求后，创建实验室预约",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab_id": {"type": "integer"},
                    "reservation_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "start_time": {"type": "string", "description": "HH:MM"},
                    "end_time": {"type": "string", "description": "HH:MM"},
                    "purpose": {"type": "string"},
                },
                "required": ["lab_id", "reservation_date", "start_time", "end_time", "purpose"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    # 其余工具（search_lab_docs、get_my_reservations、cancel_reservation、recommend_lab 等）见完整源码。
]
```

写工具：

```python
def create_lab_reservation(db: Session, user_id: int, arguments: dict) -> str:
    try:
        lab_id = int(arguments["lab_id"])
        reservation_date = date.fromisoformat(arguments["reservation_date"])
        start_time = time.fromisoformat(arguments["start_time"])
        end_time = time.fromisoformat(arguments["end_time"])
        # 用途没给就默认填"AI智能预约"，不强制用户提供
        purpose = str(arguments.get("purpose") or "AI智能预约").strip() or "AI智能预约"
    except (KeyError, TypeError, ValueError):
        return "预约信息格式不完整，请提供实验室、日期、开始时间、结束时间。"

    # 自动获取用户姓名，不用问用户
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    user_label = user.full_name or user.username if user else f"用户#{user_id}"

    try:
        data = ReservationCreate(
            lab_id=lab_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
        )
        created, skipped = create_reservation_record(db, user_id, data)
    except (BusinessException, ValueError) as exc:
        return getattr(exc, "message", str(exc))
    result = f"✅ 预约成功！申请人：{user_label}，{len(created)}条预约编号 {', '.join(str(r.id) for r in created)}，状态为待审核。"
    if skipped:
        result += f"跳过：{'；'.join(skipped)}"
    return result
```

代码如何工作：JSON Schema 是格式防线；`ReservationCreate` 是参数防线；`create_reservation_record` 是业务和并发防线。图内的 `execute_tools_node` 和图外的 `run_model_tools()` 都统一经 `_execute_tool` 分发；写预约前会再检查当前轮是否明确确认（`_execute_tool` 内），`run_model_tools` 还用 `write_tool_handled` 保证一轮最多执行一次写工具。

当前实现的重要边界：工具选择与最终回答是分开的两次模型请求——先由 `run_model_tools()`（非流式）用 Chat Completions 的 `tools` 参数选工具并逐个执行（同时向前端发 `tool_start`/`tool_end`），再把工具结果拼进上下文，由 `stream_answer()` 发起流式请求生成回答；它不是同一次请求里由模型连续多轮的完整工具循环。

复现检查：比较“有哪些开放实验室”“帮我预约……”“不要帮我预约”。检查数据库记录，只有明确写意图且参数通过 Service 校验时才能新增。

## 第 24 节：LangGraph 状态、节点与图

### 知识点：`State → Node → Edge`

状态保存节点间数据；节点接收状态并返回要更新的字段；边确定执行顺序。当前图是**循环拓扑**：`retrieve → agent ⇄ tools → END`，`should_continue` 判断最后一条消息里还有没有 `tool_calls`；没有 Key 时 `agent` 节点直接执行本地规则（`local_tool_node`）。图外还有 `run_model_tools()`，负责把模型工具选择过程以 `tool_start`/`tool_end` 事件暴露给 SSE。

对应项目代码：[`backend/app/ai/agent.py`](../../backend/app/ai/agent.py)。

```python
class AgentState(TypedDict, total=False):
    """LangGraph 节点之间传递的状态。"""
    message: str
    history: list[dict[str, str]]
    user_id: int
    db: Session
    retrieved_docs: list[dict[str, str]]
    retrieval_engine: str
    tool_context: list[str]
    used_tools: list[str]
    messages: list[dict[str, Any]]
    final_answer: str


def retrieve_node(state: AgentState) -> AgentState:
    documents, engine = search_documents(state["message"])
    return {"retrieved_docs": documents, "retrieval_engine": engine}


def build_graph():
    """构建课程里画的循环图：agent → 有tool_calls → tools → agent → 没有 → END"""
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(AgentState)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", execute_tools_node)

        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "agent")

        # agent 后条件判断：有工具就去 tools，没有就 END
        graph.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", "end": END},
        )
        # tools 执行完回到 agent
        graph.add_edge("tools", "agent")

        return graph.compile(), "LangGraph循环工具"
    except ImportError:
        return None, "顺序编排（安装 langgraph 后自动启用）"
```

运行逻辑：

```python
def run_graph(message: str, user_id: int, db: Session, history=None) -> AgentState:
    initial_state: AgentState = {
        "message": message,
        "history": history or [],
        "user_id": user_id,
        "db": db,
    }
    if AGENT_GRAPH:
        return AGENT_GRAPH.invoke(initial_state)
    state = {**initial_state, **retrieve_node(initial_state)}
    return {**state, **local_tool_node(state)}
```

逐句理解：`total=False` 允许节点只返回局部状态；没有 LangGraph 包时按相同顺序手工执行（检索 + 本地工具节点），保证基础功能仍可用；装上 langgraph 后，有 Key 时的模型工具调用会走图内的 `agent ⇄ tools` 条件循环。

复现检查：画出 `retrieve`/`agent`/`tools` 各节点读写的字段，说清 `should_continue` 的去向判断，并在 `chat_stream` 中找出 `run_graph → run_model_tools → build_prompt_context → stream_answer` 的真实顺序。

## 第 25 节：SSE 流式事件与过程可见

### 知识点：SSE 帧和七种业务事件

一条 SSE 由 `event:`、`data:` 和空行组成。项目使用 `status`/`tool_start`/`tool_end`/`tool`/`token`/`done`/`error`，前端根据事件名更新过程和答案。

对应项目代码：[`backend/app/api/ai.py`](../../backend/app/api/ai.py) 生成 SSE 事件，[`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) 生成回答，[`fronted/src/api/ai.js`](../../fronted/src/api/ai.js) 解析事件流。

```python
def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
```

生成顺序已经在第 20 节完整函数中出现；前端解析缓冲区在第 21 节出现。这里重点看回答来源：

```python
def stream_answer(message: str, history: list[dict[str, str]], context: str):
    """有 Key 时流式输出回答。"""
    if not settings.OPENAI_API_KEY:
        answer = (
            "我已根据本地知识库和系统实时数据完成查询。\n\n"
            f"{context}\n\n"
            "如需由 AI 直接创建预约，请按 预约实验室ID 1 2026-10-01 09:00-11:00 用途：课程实验 的格式告诉我。"
        )
        for index in range(0, len(answer), 12):
            yield answer[index : index + 12]
        return

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": (
            "你是实验室信息查询助手。根据知识库和工具结果准确、简洁地回答用户问题，"
            "不要编造实验室、设备或预约状态。只回答用户提出的问题。"
        )},
        *history[-10:],
        {"role": "user", "content": f"用户问题：{message}\n\n{context}"},
    ]
    stream = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
```

这段就是当前项目的完整 `stream_answer` 函数。无 Key 时每 12 个字符切片只是模拟流式展示，**不是模型 token**；有 Key 时用 Chat Completions `stream=True` 读取 `delta.content` 逐 token 输出。`history[-10:]` 控制上下文长度，system 指令要求模型不能编造实验室、设备或预约状态。

复现检查：在浏览器 Network 观察事件顺序；解释为什么后端帧以空行结束、前端为什么要保留未完成的 buffer。

## 第 26 节：首页统计与课程收尾

### 知识点：SQL 聚合和角色数据范围

统计应在数据库端用 `COUNT/SUM` 完成，而不是下载所有行给前端计算。学生只能看到自己的预约统计，管理员看到全局并多一个用户数。

对应项目代码：[`backend/app/api/stats.py`](../../backend/app/api/stats.py)。

```python
@router.get("/summary")
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservation_query = db.query(func.count(Reservation.id))
    pending_query = reservation_query.filter(Reservation.status == "pending")
    if not current_user.is_superuser:
        reservation_query = reservation_query.filter(
            Reservation.user_id == current_user.id
        )
        pending_query = pending_query.filter(
            Reservation.user_id == current_user.id
        )

    data = {
        "lab_count": db.query(func.count(Lab.id)).filter(Lab.status == 1).scalar() or 0,
        "equipment_count": db.query(
            func.coalesce(func.sum(Equipment.quantity), 0)
        ).filter(Equipment.status == 1).scalar() or 0,
        "reservation_count": reservation_query.scalar() or 0,
        "pending_count": pending_query.scalar() or 0,
    }
    if current_user.is_superuser:
        data["user_count"] = db.query(func.count(User.id)).scalar() or 0
    return Response.success(data=data)
```

前端根据角色派生卡片：

```js
const statItems = computed(() => {
  const items = [
    { key: 'lab_count', label: '开放实验室', icon: markRaw(Collection), color: '#ecf5ff', path: '/lab' },
    { key: 'equipment_count', label: '可用设备数量', icon: markRaw(Monitor), color: '#f0f9eb', path: '/equ' },
    { key: 'reservation_count', label: isAdmin.value ? '全部预约' : '我的预约', icon: markRaw(Calendar), color: '#fdf6ec', path: '/reservation' },
    { key: 'pending_count', label: '待审核预约', icon: markRaw(Calendar), color: '#fef0f0', path: '/reservation' }
  ]
  if (isAdmin.value) items.push({ key: 'user_count', label: '系统用户', icon: markRaw(User), color: '#f4f4f5', path: '/user' })
  return items
})
```

代码如何工作：数据范围先由后端限制，前端只是展示；`markRaw` 避免把图标组件对象做代理；带 `path` 的卡片可点击跳转对应页面。当前设备统计检查设备状态，但不会联动实验室开放状态。

复现检查：学生与管理员分别登录，比较预约和用户统计；然后运行前端构建和后端单元测试。

## 第 27 节：用两条主链复盘整个项目

### 知识点：普通业务链与 AI 链的共同安全边界

对应项目代码：普通预约入口见 [`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue) 和 [`backend/app/services/reservation.py`](../../backend/app/services/reservation.py)；AI 入口见 [`fronted/src/views/chat.vue`](../../fronted/src/views/chat.vue) 和 [`backend/app/api/ai.py`](../../backend/app/api/ai.py)。

```text
普通预约：
lab.vue
  → createReservationApi
  → POST /api/reservations
  → get_current_user + ReservationCreate
  → create_reservation_record
  → MySQL pending 记录
  → reservation.vue 展示/审核

AI 对话：
chat.vue → store chat.js
  → streamChatApi(fetch + JWT)
  → POST /api/ai/chat/stream
  → run_graph(RAG + agent：无 Key 本地规则 / 有 Key 循环工具)
  → run_model_tools(配置 Key 时，逐个 tool_start/tool_end)
  → build_prompt_context
  → stream_answer
  → SSE
  → store 增量更新
```

AI 预约最终仍调用普通预约 Service：

```python
# backend/app/ai/tools.py
data = ReservationCreate(
    lab_id=lab_id,
    reservation_date=reservation_date,
    start_time=start_time,
    end_time=end_time,
    purpose=purpose,
)
reservation = create_reservation_record(db, user_id, data)
```

这几行是项目架构里最重要的复用点：AI 只是增加一种输入方式，不应该另写一套时间冲突、实验室状态和并发规则。否则网页预约与 AI 预约会出现不同结果。

复现检查：

1. 从 `lab.vue` 追踪一次普通预约直到 `db.commit()`。
2. 从 `chat.vue` 追踪一次 AI 问答直到 SSE `token`。
3. 指出身份校验、参数校验、业务校验和数据库约束分别在哪个文件。
4. 说明 Markdown 知识、ChromaDB 索引、MySQL 业务数据为什么不能混在一起。

## 学完后的代码自测

不要只背术语。能结合代码回答下面的问题，才算真正掌握：

1. 为什么 `request` 拦截器返回统一响应后，页面读取的是 `res.data`？
2. 为什么前端有路由守卫，后端还必须使用 `Depends(get_current_user)`？
3. 为什么注册要“先查重，再捕获 `IntegrityError`”？
4. 为什么修改密码后，旧 Token 即使还没到 `exp` 也会失效？
5. 为什么时间冲突用两个不等式，而不是只比较开始时间？
6. 为什么 AI 创建预约必须复用 `create_reservation_record()`？
7. 为什么一个 `reader.read()` 不能直接当作一条 SSE 事件？
8. 当前本地哈希向量和真正语义 Embedding 有什么差别？
9. 当前 LangGraph 图内、图外各自执行什么？
10. 有模型 Key 时，一次聊天为什么可能产生两次模型 API 请求？

需要查看某个文件的完整上下文时，使用本节的源码链接；需要逐文件完整抄写时，再查 [`full-reference.md`](full-reference.md)。这份同步学习版应当作为首选入口，避免在“纯解释”和“纯源码”两份文档之间来回跳转。
