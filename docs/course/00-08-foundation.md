# 第 00–08 节：从项目骨架到前后端登录联调（知识点 ↔ 完整代码对照）

> 本份是「**知识点 ↔ 完整代码**」对照版：每节课先列出知识点清单，再把实现这些知识点的**当前项目完整源码**直接贴出来（含 import、完整函数、Vue 完整 `<template>` 与 `<script setup>`）。纯 CSS 样式与知识点无关，省略时会在注释里标明。代码均按本仓库核对；前端文件夹实际拼作 `fronted`。
>
> 学习方法：先看「知识点清单」，对照「知识点的具体代码」定位到函数/组件，再按「完整源码」把整份文件手敲或断点调试一遍，最后做「验证」。

## 第 00 节：认识完整项目与一次请求

**知识点清单：** 应用入口（Vue / FastAPI）、页面路由、HTTP 客户端与接口函数、后端路由与鉴权、数据验证与存储、AI 层与流式输出；以及“前端隐藏按钮 ≠ 权限，后端依赖才是权限”这条主线。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| Vue 应用挂载 | [`fronted/src/main.js`](../../fronted/src/main.js) | `createApp(App)` + `app.mount('#app')` |
| FastAPI 应用入口 | [`backend/app/main.py`](../../backend/app/main.py) | `app = FastAPI()` + `app.include_router(api)` |
| URL 到页面组件 | [`fronted/src/router/index.js`](../../fronted/src/router/index.js) | `createRouter` 的 `routes` 与 `beforeEach` |
| 后端按业务分组 | [`backend/app/api/__init__.py`](../../backend/app/api/__init__.py) | `APIRouter(prefix="/api")` 汇总各子路由 |
| HTTP 客户端 | [`fronted/src/utils/request.js`](../../fronted/src/utils/request.js) | axios 实例与拦截器 |
| 鉴权依赖 | [`backend/app/dependencies/auth.py`](../../backend/app/dependencies/auth.py) | `get_current_user` |
| ORM 与校验 | [`backend/app/models/`](../../backend/app/models/)、[`backend/app/schemas/`](../../backend/app/schemas/) | 数据库模型与 Pydantic 模型 |

一次“查看我的资料”的真实调用链（对照文件即可定位每一环）：

```text
浏览器 /user
  → fronted/src/router/index.js：本地有无 Token（只改善体验）
  → fronted/src/views/user.vue → fronted/src/api/user.js → GET /api/user/info
  → fronted/src/utils/request.js：加 Authorization: Bearer <Token>
  → backend/app/main.py → backend/app/api/__init__.py → backend/app/api/user.py
  → backend/app/dependencies/auth.py：解码 JWT、查用户、校验状态与密码版本
  → backend/app/schemas/user.py：ORM User → UserResponse
  → backend/app/common/response.py：返回 {code, message, data}
  → Vue 更新画面
```

**验证：** 打开浏览器开发者工具 Network，找到 `GET /api/user/info`；失败时依次区分“Vite 页面打不开”“8000 端口不通”“返回 401”“返回 500”。完整全局图见 [`ARCHITECTURE.md`](../../ARCHITECTURE.md)。

## 第 01 节：环境、依赖与配置

**知识点清单：** Node/npm 与 Vite、Python 虚拟环境、`@` 路径别名、后端环境变量读取（pydantic-settings）、前后端 `.env` 的职责区别、依赖清单。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 脚本与依赖 | [`fronted/package.json`](../../fronted/package.json) | `scripts`、`dependencies`、`devDependencies` |
| Vite 插件与别名 | [`fronted/vite.config.js`](../../fronted/vite.config.js) | `plugins`、`resolve.alias['@']` |
| 后端读取 .env | [`backend/app/config.py`](../../backend/app/config.py) | `BaseSettings` + `SettingsConfigDict(env_file=...)` |
| 后端依赖清单 | [`backend/requirements-all.txt`](../../backend/requirements-all.txt) | 直接依赖列表 |
| 环境变量样例 | [`backend/.env.example`](../../backend/.env.example)、[`fronted/.env.example`](../../fronted/.env.example) | 各自字段的用途 |

**完整源码：**

[`fronted/package.json`](../../fronted/package.json)（当前完整内容）：

```json
{
  "name": "fronted",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "format": "prettier --write --experimental-cli src/"
  },
  "dependencies": {
    "@element-plus/icons-vue": "^2.3.2",
    "axios": "^1.20.0",
    "element-plus": "^2.14.5",
    "vue": "^3.5.40",
    "vue-router": "^5.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.8",
    "prettier": "3.9.5",
    "vite": "^8.1.5",
    "vite-plugin-vue-devtools": "^8.1.5"
  },
  "engines": {
    "node": "^22.18.0 || >=24.12.0"
  }
}
```

[`fronted/vite.config.js`](../../fronted/vite.config.js)（当前完整内容，`@` 别名让后续写 `@/api/auth` 而不是相对路径）：

```js
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
```

[`backend/app/config.py`](../../backend/app/config.py)（当前完整内容）：

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 定位到 backend/.env，不受终端当前目录影响
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # 数据库连接地址，从 .env 中读取
    DATABASE_URL: str
    # JWT 配置
    JWT_SECRET_KEY: str
    JWT_EXPIRE_HOURS: int
    JWT_ALGORITHM: str = "HS256"
    # AI 配置均为可选；不配置 Key 时系统使用本地知识库回答。
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 其他文件通过 settings 读取配置
settings = Settings()
```

[`backend/.env.example`](../../backend/.env.example)（字段含义；真实值只写进本机 `backend/.env`）：

```text
# MySQL 数据库需要先创建，例如：CREATE DATABASE lab_agent CHARACTER SET utf8mb4;
DATABASE_URL=mysql+pymysql://root:your_password@127.0.0.1:3306/lab_agent

# 请在实际项目中换成足够长的随机字符串。
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_EXPIRE_HOURS=24
JWT_ALGORITHM=HS256

# AI 配置可选：不填写 Key 时，助手使用本地知识库降级模式。
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4.1-mini
```

[`fronted/.env.example`](../../fronted/.env.example)（前端只能放接口地址，不能放密钥）：

```text
# 后端 FastAPI 服务地址。复制为 .env.development 后可按本机端口修改。
VITE_API_BASE_URL=http://127.0.0.1:8000
```

[`backend/requirements-all.txt`](../../backend/requirements-all.txt)（当前完整内容）：

```text
# 项目直接依赖。这里不锁死传递依赖版本，减少 Python 小版本升级时的冲突。
fastapi>=0.141.1
uvicorn[standard]>=0.53.0
SQLAlchemy>=2.0.54
PyMySQL>=1.2.0
pydantic>=2.13.5
pydantic-settings>=2.15.0
email-validator>=2.3.0
python-multipart>=0.0.32
bcrypt>=5.0.0
PyJWT>=2.13.0
openai>=2.0.0
langgraph>=1.0.0
chromadb>=1.0.0
```

**启动命令（对应上面的脚本）：**

```powershell
cd 'F:\fastapi项目实战\lab_agent\fronted'
npm install
npm run dev       # 启动 Vite；终端会给出访问地址
npm run build     # 检查生产构建

cd '..\backend'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-all.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**验证：** Vite 页面可打开；后端 `http://127.0.0.1:8000/docs` 可打开。`Settings()` 报缺少字段说明 `.env` 位置/命名不对；MySQL 连接失败先确认数据库服务和库名，不要把 ApiPost 当成数据库或后端。

## 第 02 节：Vue 入口、路由与后台主框架

**知识点清单：** `createApp` 挂载、`#app` 挂载点、`App.vue` 只有 `<router-view>`、嵌套路由（父 `/` + 子页）、`meta.requiresAuth` + `beforeEach` 路由守卫、Element Plus 注册、布局组件里的菜单与子页出口、`userReady` 先确认用户再挂载子页。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 挂载点 | [`fronted/index.html`](../../fronted/index.html) | `<div id="app"></div>` |
| 创建并注册应用 | [`fronted/src/main.js`](../../fronted/src/main.js) | `createApp(App)` + 批量注册图标 + `app.use(router)` |
| 根出口 | [`fronted/src/App.vue`](../../fronted/src/App.vue) | 单个 `<router-view />` |
| 嵌套路由与守卫 | [`fronted/src/router/index.js`](../../fronted/src/router/index.js) | `routes` + `beforeEach` |
| 布局与菜单 | [`fronted/src/layouts/layouts.vue`](../../fronted/src/layouts/layouts.vue) | `<el-menu router>` + 第二层 `<router-view v-if="userReady">` |

**完整源码：**

[`fronted/src/main.js`](../../fronted/src/main.js)（当前完整内容）：

```js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import './assets/css/global.css'
const app = createApp(App)
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

[`fronted/src/App.vue`](../../fronted/src/App.vue)（当前完整内容，只有一个一级出口）：

```vue
<template>
  <router-view />
</template>
```

[`fronted/src/router/index.js`](../../fronted/src/router/index.js)（当前完整内容）：

```js
import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/auth'

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
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/home.vue')
        },
        {
          path: 'lab',
          name: 'Lab',
          component: () => import('@/views/lab.vue')
        },
        {
          path: 'equ',
          name: 'Equ',
          component: () => import('@/views/equ.vue')
        },
        {
          path: 'user',
          name: 'User',
          component: () => import('@/views/user.vue')
        },
        {
          path: 'reservation',
          name: 'Reservation',
          component: () => import('@/views/reservation.vue')
        },
        {
          path: 'chat',
          name: 'Chat',
          component: () => import('@/views/chat.vue')
        }
      ]
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login.vue')
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/register.vue')
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/home'
    }
  ]
})

// 路由守卫负责页面级鉴权；接口级安全仍由后端 JWT 校验保证。
router.beforeEach((to) => {
  const token = getToken()
  if (to.meta.requiresAuth && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if ((to.path === '/login' || to.path === '/register') && token) {
    return '/home'
  }
})

export default router
```

[`fronted/src/layouts/layouts.vue`](../../fronted/src/layouts/layouts.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 为纯 CSS 表现，省略）：

```vue
<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand">
        <img :src="logo" alt="系统 Logo" />
        <span>智能实验室预约系统</span>
      </div>

      <el-dropdown trigger="click" @command="handleCommand">
        <button type="button" class="user-button">
          <el-avatar :size="34" :icon="UserFilled" />
          <span class="user-name">{{ displayName }}</span>
          <el-tag :type="isAdmin ? 'danger' : 'success'" size="small">
            {{ isAdmin ? '管理员' : '学生' }}
          </el-tag>
          <el-icon><ArrowDown /></el-icon>
        </button>

        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人中心</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-header>

    <el-container class="app-body">
      <el-aside class="app-aside" width="220px">
        <el-menu router :default-active="$route.path" class="app-menu">
          <el-menu-item index="/home">
            <el-icon><DataBoard /></el-icon>
            <span>系统首页</span>
          </el-menu-item>
          <el-menu-item index="/lab">
            <el-icon><House /></el-icon>
            <span>{{ isAdmin ? '实验室管理' : '实验室列表' }}</span>
          </el-menu-item>
          <el-menu-item index="/equ">
            <el-icon><Setting /></el-icon>
            <span>{{ isAdmin ? '设备管理' : '设备列表' }}</span>
          </el-menu-item>
          <el-menu-item index="/reservation">
            <el-icon><Calendar /></el-icon>
            <span>{{ isAdmin ? '预约审核' : '我的预约' }}</span>
          </el-menu-item>
          <el-menu-item index="/chat">
            <el-icon><ChatDotRound /></el-icon>
            <span>AI 实验室助手</span>
          </el-menu-item>
          <el-menu-item index="/user">
            <el-icon><User /></el-icon>
            <span>{{ isAdmin ? '用户管理' : '个人中心' }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-main class="app-main">
        <!--
          先确认完当前用户再挂载子页。
          Vue 的子组件 mounted 会早于父组件 mounted；如果立即渲染 router-view，
          子页可能先用 localStorage 中的旧角色请求错误的列表接口。
        -->
        <router-view v-if="userReady" />
        <div v-else v-loading="true" class="page-loading" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowDown,
  Calendar,
  ChatDotRound,
  DataBoard,
  House,
  Setting,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import { getUserInfoApi } from '@/api/user'
import { useUser } from '@/utils/user'
import logo from '@/assets/css/images/logo.png'

const router = useRouter()
const { userInfo, isAdmin, updateUser, clearLoginData } = useUser()
const displayName = computed(() => userInfo.value?.full_name || userInfo.value?.username || '用户')
const userReady = ref(false)

onMounted(async () => {
  // 每次进入主框架都向后端确认一次用户信息，避免角色或状态变更后仍使用旧缓存。
  try {
    const res = await getUserInfoApi()
    updateUser(res.data)
    userReady.value = true
  } catch (error) {
    const unauthorized = error?.code === 401 || error?.response?.status === 401
    // 401 会由请求拦截器跳转登录页，此时不再挂载业务子页。
    // 若只是临时网络故障，则允许用已缓存资料进入页面，不让界面永久卡在加载态。
    if (!unauthorized) userReady.value = true
  }
})

const handleCommand = async (command) => {
  if (command === 'profile') {
    await router.push('/user')
  }
  if (command === 'logout') {
    clearLoginData()
    await router.replace('/login')
  }
}
</script>
```

**数据流：** 输入 `/home` → `beforeEach` 检查本地 Token → `App.vue` 出口渲染布局 → 布局先 `getUserInfoApi()` 确认用户，`userReady` 为真后才渲染子页 → 子出口渲染 `home.vue`。

**验证：** 未登录访问 `/home` 被带到 `/login?redirect=%2Fhome`；登录后切菜单只替换中间内容。刷新子路由报 404 说明生产部署时服务器未把未知前端路径回退到 `index.html`。

## 第 03 节：Vue 登录表单（响应式、校验、提交状态）

**知识点清单：** `reactive` 表单对象、`ref` 管理 DOM/组件引用与布尔状态、`v-model` 双向绑定、Element Plus `rules` + `validate()` 前端校验、`try/finally` 复位加载态、登录后保存并回跳。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 响应式表单与校验规则 | [`fronted/src/views/login.vue`](../../fronted/src/views/login.vue) | `form`、`rules`、`loginFormRef` |
| 提交与加载态 | 同文件 | `login()` 的 `validate()` 与 `finally` |
| 登录接口 | [`fronted/src/api/auth.js`](../../fronted/src/api/auth.js) | `loginApi` |
| 保存登录结果 | [`fronted/src/utils/user.js`](../../fronted/src/utils/user.js) | `saveLoginData` |

**完整源码：**

[`fronted/src/views/login.vue`](../../fronted/src/views/login.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 为纯 CSS，省略）：

```vue
<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="brand-block">
        <img :src="logo" alt="系统 Logo" />
        <div>
          <h1>智能实验室预约系统</h1>
          <p>登录后管理实验室、设备与预约</p>
        </div>
      </div>

      <el-form ref="loginFormRef" :model="form" :rules="rules" @submit.prevent="login">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            :prefix-icon="User"
            size="large"
            placeholder="请输入用户名"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            :prefix-icon="Lock"
            type="password"
            size="large"
            placeholder="请输入密码"
            autocomplete="current-password"
            show-password
            @keyup.enter="login"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="loadingValue"
          class="submit-button"
        >
          登录
        </el-button>

        <div class="auth-link">
          还没有账号？
          <router-link to="/register">立即注册</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'
import logo from '@/assets/css/images/logo.png'

const route = useRoute()
const router = useRouter()
const { saveLoginData } = useUser()
const loginFormRef = ref(null)
const loadingValue = ref(false)

const form = reactive({
  username: '',
  password: ''
})

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

    // 如果用户是被路由守卫拦下的，登录后回到原页面，否则进入首页。
    const redirectPath = typeof route.query.redirect === 'string' ? route.query.redirect : '/home'
    await router.replace(redirectPath)
  } finally {
    loadingValue.value = false
  }
}
</script>
```

[`fronted/src/api/auth.js`](../../fronted/src/api/auth.js)（当前完整内容）：

```js
import request from '@/utils/request'

export function loginApi(data) {
  return request.post('/api/auth/login', data)
}

export function registerApi(data) {
  return request.post('/api/auth/register', data)
}
```

[`fronted/src/utils/user.js`](../../fronted/src/utils/user.js)（当前完整内容）：

```js
import { computed, ref } from 'vue'
import { getUserInfo, logout, setToken, setUserInfo } from './auth'

// 放在 useUser 外部，使所有组件拿到的是同一个响应式用户对象。
const userInfo = ref(getUserInfo())

export function useUser() {
  const isAdmin = computed(() => Boolean(userInfo.value?.is_superuser))

  function saveLoginData(data) {
    setToken(data.token)
    updateUser(data.user)
  }

  function updateUser(user) {
    setUserInfo(user)
    userInfo.value = user
  }

  function reloadUser() {
    userInfo.value = getUserInfo()
  }

  function clearLoginData() {
    logout()
    userInfo.value = null
  }

  return {
    userInfo,
    isAdmin,
    saveLoginData,
    updateUser,
    reloadUser,
    clearLoginData
  }
}
```

**数据流：** 用户输入 → `form` → `validate()` → `POST /api/auth/login` → 后端返回 `{data: {token, user}}` → `saveLoginData(res.data)` 存 Token/用户 → `router.replace`。前端不保存密码；即使绕过表单校验，后端仍必须查库并验证哈希。

**验证：** 空用户名/密码不发请求；连点两次只提交一次；正确账号进入原目标页，错误账号收到统一错误提示。若 `res.data.token` 是 `undefined`，说明没有用本项目的 `loginApi` + 统一响应解析。

## 第 04 节：FastAPI 入口、数据库依赖与 CORS

**知识点清单：** `FastAPI()` 应用、`APIRouter` 分业务、`Depends(get_db)` 提供会话、SQLAlchemy `engine`/`SessionLocal`/`Base`、`yield/finally` 关闭连接、ORM 模型继承公共字段、CORS 配置、`Base.metadata.create_all` 只建表不建库。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 应用入口与 CORS | [`backend/app/main.py`](../../backend/app/main.py) | `app = FastAPI()`、`add_middleware(CORSMiddleware)` |
| 引擎 / 会话 / 公共字段 | [`backend/app/database.py`](../../backend/app/database.py) | `engine`、`SessionLocal`、`get_db()`、`Base` |
| 路由汇总 | [`backend/app/api/__init__.py`](../../backend/app/api/__init__.py) | `APIRouter(prefix="/api")` |
| 第一张业务表 | [`backend/app/models/user.py`](../../backend/app/models/user.py) | `class User(Base)` |
| 模型注册入口 | [`backend/app/models/__init__.py`](../../backend/app/models/__init__.py) | 导入各模型 |

**完整源码：**

[`backend/app/main.py`](../../backend/app/main.py)（当前完整内容）：

```python
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
from app.database import Base, engine
from app.models import Equipment, Lab, Reservation, User  # noqa: F401 - 注册 ORM 模型
from app.api.upload import UPLOAD_DIR

# 创建尚不存在的数据库表，数据库本身需要提前创建
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 上传目录通过 /uploads 暴露，前端可直接预览上传后的图片。
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 配置跨域请求
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

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
```

[`backend/app/database.py`](../../backend/app/database.py)（当前完整内容）：

```python
from collections.abc import Generator
from datetime import datetime

from sqlalchemy import DateTime, create_engine, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from .config import settings

# 创建数据库连接引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)


# 创建数据库会话工厂
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# FastAPI 数据库依赖
# 每次接口请求时创建一个 Session，请求结束后自动关闭
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# 所有 ORM 模型的父类
class Base(DeclarativeBase):
    # 自增主键
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # 创建时间：新增数据时自动生成
    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    # 更新时间：新增时生成，修改数据时自动更新
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
```

[`backend/app/api/__init__.py`](../../backend/app/api/__init__.py)（当前完整内容）：

```python
from fastapi import APIRouter
from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.equipment import router as equipment_router
from app.api.lab import router as lab_router
from app.api.reservation import router as reservation_router
from app.api.stats import router as stats_router
from app.api.upload import router as upload_router
from app.api.user import router as user_router

api = APIRouter(prefix="/api")

api.include_router(auth_router)
api.include_router(user_router)
api.include_router(upload_router)
api.include_router(lab_router)
api.include_router(equipment_router)
api.include_router(reservation_router)
api.include_router(stats_router)
api.include_router(ai_router)
```

[`backend/app/models/__init__.py`](../../backend/app/models/__init__.py)（当前完整内容）：

```python
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User

__all__ = ["User", "Lab", "Equipment", "Reservation"]
```

[`backend/app/models/user.py`](../../backend/app/models/user.py)（当前完整内容）：

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    # 数据库表名，前后都是两个下划线
    __tablename__ = "users"

    # 表注释
    __table_args__ = {"comment": "用户表"}

    # id、create_time、update_time 从 Base 继承，不需要重复定义

    # 用户名：必填、不可重复
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名",
    )

    # 只保存密码哈希，禁止保存用户输入的明文密码
    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希值，非明文密码",
    )

    # 邮箱：必填、不可重复
    email: Mapped[str] = mapped_column(
        String(254),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱",
    )

    # 姓名：允许不填写，因此类型也允许 None
    full_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="姓名",
    )

    # 账号是否启用：默认启用
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="账号是否启用：True启用，False禁用",
    )

    # 是否为超级管理员：默认普通用户
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为超级管理员：True是，False否",
    )
```

**验证：** 启动后 `/` 返回 `{"message":"FastAPI工程正在运行中"}`，`/docs` 出现接口文档。报 `Unknown database` 先建库；报连接拒绝先查 MySQL 服务/端口；CORS 报错检查 `allow_origins` 与实际 Origin 是否一致。`create_all` 不创建 MySQL 数据库本身，也不更新已存在表的旧结构。

## 第 05 节：登录 API（校验、查用户、密码哈希）

**知识点清单：** Pydantic 解析请求体、SQLAlchemy 按用户名查 ORM `User`、bcrypt `verify_password` 比对、401/403 区分、`UserResponse` 隐藏密码、`create_access_token` 签发 Token。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 请求/响应形状 | [`backend/app/schemas/auth.py`](../../backend/app/schemas/auth.py) | `LoginRequest`、`LoginResponse` |
| 响应隐藏密码 | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `UserResponse`（不声明 `password`） |
| 密码哈希与校验 | [`backend/app/utils/password.py`](../../backend/app/utils/password.py) | `hash_password`、`verify_password` |
| 登录接口 | [`backend/app/api/auth.py`](../../backend/app/api/auth.py) | `login()` |

**完整源码：**

[`backend/app/schemas/auth.py`](../../backend/app/schemas/auth.py)（当前完整内容）：

```python
from pydantic import BaseModel

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
```

[`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) 中的 `UserResponse`（当前完整内容；刻意不声明 `password`）：

```python
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    create_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

[`backend/app/utils/password.py`](../../backend/app/utils/password.py)（当前完整内容）：

```python
import bcrypt

def hash_password(password: str) -> str:
    """对密码加密"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    """验证密码的有效性"""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (TypeError, ValueError):
        return False
```

[`backend/app/api/auth.py`](../../backend/app/api/auth.py) 中的 `login()`（当前完整函数；`register()` 在第 09 节）：

```python
router = APIRouter(prefix="/auth", tags=["权限验证"])


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # 根据用户账号查询数据库
    user = db.query(User).filter(User.username == data.username).first()

    # 判断账号和密码是否正确
    if not user or not verify_password(data.password, user.password):
        # 登录凭证错误属于 401，而不是服务器内部错误。
        raise BusinessException(code=BizCode.UNAUTHORIZED, message="账号或密码错误")
    # 验证账号的状态
    if not user.is_active:
        # 凭证本身正确，但账号状态不允许继续访问，因此返回 403。
        raise BusinessException(code=BizCode.FORBIDDEN, message="账号被禁用")
    # 创建token
    token = create_access_token(user.id, user.password)
    # 返回信息
    return Response.success(
        message="登录成功",
        data=LoginResponse(token=token, user=UserResponse.model_validate(user)),
    )
```

**数据流：** `POST /api/auth/login` → `LoginRequest` 解析 → `get_db` 会话 → `User.username` 查询 → `bcrypt.checkpw` → `create_access_token()` → `UserResponse.model_validate(user)` → `{code: 200, message, data: {token, user}}`。

**验证：** 在 `/docs` 用已有测试账号发 `{"username":"...","password":"..."}`；成功 HTTP 200 且 `data.user` 无 `password`；错误密码 HTTP 401；禁用账号 HTTP 403。不要在笔记/聊天里粘贴真实 Token 或密码。

## 第 06 节：JWT 签发、Bearer 鉴权与管理员权限

**知识点清单：** JWT 签名/过期/解码、`OAuth2PasswordBearer` 提取 Bearer、解码后仍查库校验、密码版本指纹让改密后旧 Token 失效、`hmac.compare_digest` 恒定时间比较、`get_current_admin` 二次授权。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 签发/解码 JWT | [`backend/app/utils/jwt.py`](../../backend/app/utils/jwt.py) | `build_password_version`、`create_access_token`、`decode_access_token` |
| 当前用户依赖 | [`backend/app/dependencies/auth.py`](../../backend/app/dependencies/auth.py) | `oauth2_scheme`、`get_current_user` |
| 管理员依赖 | [`backend/app/dependencies/permission.py`](../../backend/app/dependencies/permission.py) | `get_current_admin` |

**完整源码：**

[`backend/app/utils/jwt.py`](../../backend/app/utils/jwt.py)（当前完整内容）：

```python
import hashlib
from datetime import datetime, timedelta

import jwt

from app.config import settings


def build_password_version(password_hash: str) -> str:
    """生成密码版本指纹，用于让改密前签发的 Token 自动失效。

    JWT 只保存哈希的 SHA-256 指纹，不暴露数据库里的 bcrypt 密码哈希。
    用户修改密码后 bcrypt 哈希发生变化，鉴权时指纹不再匹配旧 Token。
    """
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def create_access_token(user_id: int, password_hash: str) -> str:
    """创建带过期时间和密码版本的 JWT Token。"""
    expire = datetime.now() + timedelta(hours=settings.JWT_EXPIRE_HOURS)

    payload = {
        "user_id": user_id,
        "password_version": build_password_version(password_hash),
        "exp": expire,  # exp 是 JWT 标准字段，PyJWT 会自动校验。
    }

    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

def decode_access_token(token: str) -> dict:
    """解析jwt token"""
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
```

[`backend/app/dependencies/auth.py`](../../backend/app/dependencies/auth.py)（当前完整内容）：

```python
import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.jwt import build_password_version, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """JWT token 鉴权验证合法性"""
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录"
        )
    # 获取到用户ID
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登录凭证"
        )
    # 从数据库根据用户ID查询用户信息
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户被禁用"
        )
    password_version = payload.get("password_version", "")
    if not hmac.compare_digest(
        password_version,
        build_password_version(user.password),
    ):
        # 修改密码后旧 Token 的指纹与当前密码不一致，强制重新登录。
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码已修改，请重新登录",
        )
    return user
```

[`backend/app/dependencies/permission.py`](../../backend/app/dependencies/permission.py)（当前完整内容）：

```python
from fastapi import Depends

from app.common.exceptions import BusinessException
from app.common.response import BizCode
from app.dependencies.auth import get_current_user
from app.models.user import User


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """验证当前用户是否为管理员，供后台管理接口复用。"""
    if not current_user.is_superuser:
        raise BusinessException(code=BizCode.FORBIDDEN, message="当前账号没有管理权限")
    return current_user
```

**数据流：** 请求头 Bearer → `oauth2_scheme` 提取 Token → `decode_access_token` 校验签名与 `exp` → 查用户 → 校验启用状态与密码版本 → 注入 `User`。管理员接口再走 `get_current_admin`。

**验证：** 登录后复制 Token，给 `GET /api/user/info` 设置 `Authorization: Bearer <token>`；不带/篡改 Token 返回 401，普通用户请求管理员接口返回 403。`/docs` 的 OAuth2 表单用 form 方式换 Token，而当前登录接口收 JSON，直接用它可能 422，用 ApiPost 手工设置 Bearer 头即可。

## 第 07 节：统一响应与全局异常处理

**知识点清单：** `code/message/data` 统一结构、HTTP 状态码真实反映错误（400/401/403/500）、业务异常/HTTP 异常/参数校验异常/未知异常分别处理、500 堆栈只进后端日志。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 统一响应模型 | [`backend/app/common/response.py`](../../backend/app/common/response.py) | `BizCode`、`Response.success/error` |
| 业务异常与四个处理器 | [`backend/app/common/exceptions.py`](../../backend/app/common/exceptions.py) | `BusinessException` + 四个 handler |
| 处理器注册 | [`backend/app/main.py`](../../backend/app/main.py) | `add_exception_handler(...)` |

**完整源码：**

[`backend/app/common/response.py`](../../backend/app/common/response.py)（当前完整内容）：

```python
from enum import IntEnum
from typing import Any

from pydantic import BaseModel


class BizCode(IntEnum):
    """前后端约定的业务状态码。"""

    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500


class Response(BaseModel):
    """统一封装的返回格式"""

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

[`backend/app/common/exceptions.py`](../../backend/app/common/exceptions.py)（当前完整内容）：

```python
import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.response import Response, BizCode

logger = logging.getLogger("lab_agent")


class BusinessException(Exception):
    """自定义业务异常"""

    def __init__(self, message: str, code: int = BizCode.INTERNAL_ERROR):
        self.message = message
        self.code = code
        super().__init__(message)


async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器。

    响应体仍保持项目统一的 ``code/message/data`` 结构，同时让 HTTP 状态码
    真实反映错误类型。这样浏览器、ApiPost、反向代理和监控系统都能正确判断
    请求是否成功，而不需要只依赖响应体中的业务码。
    """
    logger.warning(f"业务异常 | 路径:{request.url.path} | 错误:{exc.message}")
    code = int(exc.code)
    http_status = code if 400 <= code <= 599 else int(BizCode.INTERNAL_ERROR)
    return JSONResponse(
        status_code=http_status,
        content=Response.error(code=exc.code, message=exc.message).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP原生异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=Response.error(
            code=exc.status_code, message=str(exc.detail)
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验异常：把Pydantic的具体错误提取出来给前端"""
    first_err = exc.errors()[0]
    err_field = ".".join([str(i) for i in first_err["loc"]])
    err_msg = first_err["msg"]
    detail = f"参数错误：{err_field} {err_msg}"
    return JSONResponse(
        # 参数没有通过 Pydantic 校验，属于客户端请求错误。
        status_code=int(BizCode.BAD_REQUEST),
        content=Response.error(code=BizCode.BAD_REQUEST, message=detail).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception):
    """全局兜底异常：记录完整错误栈，不把内部细节暴露给前端"""
    logger.exception(f"未捕获异常 | 路径:{request.url.path}")  # 自动打完整traceback
    return JSONResponse(
        # 未知异常使用真实 500，方便日志平台和调用方触发告警或重试。
        status_code=int(BizCode.INTERNAL_ERROR),
        content=Response.error(
            code=BizCode.INTERNAL_ERROR, message="服务器开小差了，请稍后重试"
        ).model_dump(),
    )
```

注册部分已在第 04 节 [`main.py`](../../backend/app/main.py) 的 `add_exception_handler` 中给出，这里不再重复。

**数据流：** `raise BusinessException(code=BizCode.UNAUTHORIZED, ...)` → 对应处理器 → HTTP 401 + `{"code":401,...}`；请求体不符合 Pydantic 模型 → `validation_exception_handler` 返回 400；未知异常 → 兜底处理器记堆栈到日志，只给前端通用 500。

**验证：** `POST /api/auth/login` 缺 `password` 应得 HTTP 400 且 `message` 指出字段；错误密码 HTTP 401。若接口出错但 Network 显示 200，多半没写 `JSONResponse(status_code=...)`。

## 第 08 节：axios 封装与前后端联调

**知识点清单：** axios 实例 `baseURL/timeout`、请求拦截器自动加 JWT、响应拦截器统一处理业务错误/401/超时/断网、`return response.data` 的语义、`src/api` 业务函数层、`localStorage` 存取 Token 的健壮性。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| axios 实例与拦截器 | [`fronted/src/utils/request.js`](../../fronted/src/utils/request.js) | `axios.create` + 两个拦截器 |
| Token/用户本地存储 | [`fronted/src/utils/auth.js`](../../fronted/src/utils/auth.js) | `getToken/setToken/.../logout` |
| 业务接口函数 | [`fronted/src/api/auth.js`](../../fronted/src/api/auth.js) | `loginApi`、`registerApi` |
| 开发环境地址 | [`fronted/.env.development`](../../fronted/.env.development) | `VITE_API_BASE_URL`（用途见 `.env.example`） |

**完整源码：**

[`fronted/src/utils/auth.js`](../../fronted/src/utils/auth.js)（当前完整内容）：

```js
// 登录凭证统一放在这里管理，其他组件不直接操作 localStorage。
const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUserInfo() {
  const value = localStorage.getItem(USER_KEY)
  if (!value) return null

  try {
    return JSON.parse(value)
  } catch {
    // 本地数据被手工改坏时直接清除，避免整个 Vue 应用启动失败。
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function setUserInfo(userInfo) {
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
}

export function removeUserInfo() {
  localStorage.removeItem(USER_KEY)
}

export function logout() {
  removeToken()
  removeUserInfo()
}
```

[`fronted/src/utils/request.js`](../../fronted/src/utils/request.js)（当前完整内容）：

```js
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { getToken, logout } from './auth'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 30000
})

// 每个业务请求自动携带 JWT，页面组件无需重复拼 Authorization。
request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
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
      ElMessage.error(message || '登录状态已失效，请重新登录')
      logout()
      router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else if (error.response) {
      ElMessage.error(message || '请求失败')
    } else {
      ElMessage.error('网络异常，请检查后端服务是否启动')
    }
    return Promise.reject(error)
  }
)

export default request
```

[`fronted/src/api/auth.js`](../../fronted/src/api/auth.js)（当前完整内容）：

```js
import request from '@/utils/request'

export function loginApi(data) {
  return request.post('/api/auth/login', data)
}

export function registerApi(data) {
  return request.post('/api/auth/register', data)
}
```

[`fronted/src/utils/user.js`](../../fronted/src/utils/user.js) 已在第 03 节给出完整内容，这里不重复。

**数据流：** `loginApi(form)` → axios 用 `baseURL` 拼成 `http://127.0.0.1:8000/api/auth/login` → FastAPI 返回统一 JSON → 拦截器检查 `code`，业务响应交给页面 → `saveLoginData(res.data)` → 后续请求自动带 Bearer。注意 axios 原始响应是 `{data, status, ...}`，本拦截器成功时 `return response.data`，所以页面拿到的 `res.data` 才是后端业务数据。

**验证：** 分别启动前后端，先开 `http://127.0.0.1:8000/docs` 再登录；Network 中登录 `POST /api/auth/login` 成功 `code=200`，之后 `GET /api/user/info` 带 `Authorization: Bearer ...`。`npm run build` 检查导入/语法。若提示“网络异常”，先确认 `/docs` 能打开和 `VITE_API_BASE_URL` 端口一致。

## 本组自检

- 能说出 `fronted/src/views`、`src/api`、`src/utils/request.js` 各管什么。
- 能解释 `Depends(get_db)` 为什么用 `yield/finally`。
- 能讲清 401（未登录/凭证失效）与 403（已登录但无权限）在后端 `Depends` 的落点。
- 能解释为什么前端路由守卫不是真正的权限控制。
