# 智能实验室预约系统：第 00–27 节完整对照教程（知识点 ↔ 完整代码）

> 本文件是 `docs/course/` 下四份分册（`00-08-foundation.md`、`09-14-users.md`、`15-19-business.md`、`20-27-ai.md`）的合并版，代码与项目源文件逐字一致。
>
> 如果你觉得“知识点在一处、代码在另一处”不便学习，请改看 [`LEARN_WITH_CODE.md`](LEARN_WITH_CODE.md)。它会在每个知识点后立即给出对应代码、解析和复现检查；本文件更适合查阅完整源码上下文。
>
> 体例：每节先列**知识点清单**，再用 `知识点 | 完整代码文件 | 实现该知识点的具体代码` 定位表指明落点，然后贴出实现该知识点的**完整源码**（含 import、完整函数、Vue 完整 `<template>` 与 `<script setup>`；只有与知识点无关的纯 CSS 省略时会注明）。
>
> **安全约定：** 密钥只写在 `backend/.env`；不要把 Key 写进 `VITE_` 变量（Vite 会把它打进浏览器产物）、粘贴到聊天记录或提交到仓库。不要把真实 Token 抄进笔记。数据库只存 bcrypt 哈希，不要为了测试直接插入明文密码。验证时用指定的测试账号，不要清空或重建已有的 MySQL 数据。
>
> 学完每节课后的**复习与知识点详解**见 [`review-notes.md`](review-notes.md)。

---

## 目录

- **第一部分：工程骨架、Vue、FastAPI 与登录联调**
  - [第 00 节：认识完整项目与一次请求](#第-00-节认识完整项目与一次请求)
  - [第 01 节：环境、依赖与配置](#第-01-节环境依赖与配置)
  - [第 02 节：Vue 入口、路由与后台主框架](#第-02-节vue-入口路由与后台主框架)
  - [第 03 节：Vue 登录表单（响应式、校验、提交状态）](#第-03-节vue-登录表单响应式校验提交状态)
  - [第 04 节：FastAPI 入口、数据库依赖与 CORS](#第-04-节fastapi-入口数据库依赖与-cors)
  - [第 05 节：登录 API（校验、查用户、密码哈希）](#第-05-节登录-api校验查用户密码哈希)
  - [第 06 节：JWT 签发、Bearer 鉴权与管理员权限](#第-06-节jwt-签发bearer-鉴权与管理员权限)
  - [第 07 节：统一响应与全局异常处理](#第-07-节统一响应与全局异常处理)
  - [第 08 节：axios 封装与前后端联调](#第-08-节axios-封装与前后端联调)
  - [本组自检](#本组自检)
- **第二部分：用户注册、上传、资料与用户管理**
  - [第 09 节：开发用户注册功能](#第-09-节开发用户注册功能)
  - [第 10 节：开发文件上传 API](#第-10-节开发文件上传-api)
  - [第 11 节：修改个人信息与共享用户状态](#第-11-节修改个人信息与共享用户状态)
  - [第 12 节：修改密码与旧 Token 失效](#第-12-节修改密码与旧-token-失效)
  - [第 13 节：管理员用户列表](#第-13-节管理员用户列表)
  - [第 14 节：管理员用户增删改](#第-14-节管理员用户增删改)
  - [本组自检](#本组自检)
  - [附录：`user.vue` 完整源码（本组第 10–14 节共用页面）](#附录uservue-完整源码本组第-1014-节共用页面)
- **第三部分：实验室、设备与预约业务**
  - [第 15 节：开发实验室管理功能](#第-15-节开发实验室管理功能)
  - [第 16 节：开发实验室设备管理](#第-16-节开发实验室设备管理)
  - [第 17 节：学生端与管理端的角色渲染](#第-17-节学生端与管理端的角色渲染)
  - [第 18 节：开发实验室预约功能](#第-18-节开发实验室预约功能)
  - [第 19 节：我的预约与预约审核](#第-19-节我的预约与预约审核)
  - [本组自检](#本组自检)
- **第四部分：AI 助手、RAG、Tool Calling、LangGraph 与 SSE**
  - [第 20 节：开发实验室 AI 助手对话（后端部分）](#第-20-节开发实验室-ai-助手对话后端部分)
  - [第 21 节：开发实验室 AI 助手对话（前端与联调）](#第-21-节开发实验室-ai-助手对话前端与联调)
  - [第 22 节：用 RAG 给实验室助手接入知识库](#第-22-节用-rag-给实验室助手接入知识库)
  - [第 23 节：用 Tool Calling 让助手查询实验室数据](#第-23-节用-tool-calling-让助手查询实验室数据)
  - [第 24 节：用 LangGraph 做智能预约 Agent](#第-24-节用-langgraph-做智能预约-agent)
  - [第 25 节：用 SSE 流式输出并让过程可见](#第-25-节用-sse-流式输出并让过程可见)
  - [第 26 节：完善系统首页与课程收尾](#第-26-节完善系统首页与课程收尾)
  - [第 27 节：项目图解与完整链路复盘](#第-27-节项目图解与完整链路复盘)
  - [本组自检](#本组自检)
  - [附录：`backend/app/ai/agent.py` 完整源码](#附录backendappaiagentpy-完整源码)

---

# 第一部分：工程骨架、Vue、FastAPI 与登录联调

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


---

# 第二部分：用户注册、上传、资料与用户管理

## 第 09 节：开发用户注册功能

**知识点清单：** Pydantic `Field`/`EmailStr`/`field_validator` 输入校验、ORM `unique=True` 唯一约束、bcrypt 存哈希不存明文、公开注册固定为普通用户、`IntegrityError` 兜底并发冲突、前端确认密码只校验不上送。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 输入模型与去空白校验 | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `UserCreate`、`strip_username` |
| 用户名/邮箱唯一 | [`backend/app/models/user.py`](../../backend/app/models/user.py) | `unique=True`（第 04 节已贴） |
| 密码哈希 | [`backend/app/utils/password.py`](../../backend/app/utils/password.py) | `hash_password`（第 05 节已贴） |
| 注册接口 | [`backend/app/api/auth.py`](../../backend/app/api/auth.py) | `register()` |
| 注册 API | [`fronted/src/api/auth.js`](../../fronted/src/api/auth.js) | `registerApi` |
| 注册页面 | [`fronted/src/views/register.vue`](../../fronted/src/views/register.vue) | 完整组件（见下） |

**完整源码：**

[`backend/app/schemas/user.py`](../../backend/app/schemas/user.py)（当前完整内容；本文件同时被第 11–14 节复用）：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=64)
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        """注册和管理员新增用户共用这条规则，防止全空格用户名入库。"""
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("用户名至少需要 3 个非空白字符")
        return cleaned


class AdminUserCreate(UserCreate):
    is_active: bool = True
    is_superuser: bool = False


class UserProfileUpdate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=64)


class AdminUserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    is_superuser: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        # 管理员编辑时，None 只适用于可选的姓名；邮箱、角色和状态必须有值。
        required_fields = ("email", "is_active", "is_superuser")
        if any(field in self.model_fields_set and getattr(self, field) is None for field in required_fields):
            raise ValueError("用户必填字段不能设为 null")
        return self


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

[`backend/app/api/auth.py`](../../backend/app/api/auth.py) 中的 `register()`（当前完整函数）：

```python
@router.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    """注册普通用户账号。"""
    username = data.username.strip()
    full_name = data.full_name.strip() if data.full_name else None

    if len(username) < 3:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="用户名至少需要 3 个字符")

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

[`fronted/src/api/auth.js`](../../fronted/src/api/auth.js) 中的 `registerApi`（`loginApi` 已在第 03 节）：

```js
export function registerApi(data) {
  return request.post('/api/auth/register', data)
}
```

[`fronted/src/views/register.vue`](../../fronted/src/views/register.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 省略）：

```vue
<template>
  <div class="register-container">
    <div class="register-box">
      <h2 class="register-title">注册账号</h2>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" :prefix-icon="User" placeholder="3～20 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="registerForm.email" :prefix-icon="Message" placeholder="用于账号识别" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="registerForm.full_name" :prefix-icon="Postcard" placeholder="选填" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            :prefix-icon="Lock"
            type="password"
            placeholder="8～64 个字符"
            autocomplete="new-password"
            show-password
            @change="revalidateConfirmPassword"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            :prefix-icon="Lock"
            type="password"
            placeholder="请再次输入密码"
            autocomplete="new-password"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="loadingValue"
          class="submit-button"
        >
          注册
        </el-button>

        <div class="login-link">
          已有账号？
          <router-link to="/login">返回登录</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock, Message, Postcard } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { registerApi } from '@/api/auth'

const router = useRouter()
const registerFormRef = ref(null)
const loadingValue = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  full_name: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入密码'))
  else if (value !== registerForm.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const rules = {
  username: [
    { required: true, whitespace: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为 3～20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8～64 个字符', trigger: 'blur' }
  ],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }]
}

const revalidateConfirmPassword = () => {
  if (registerForm.confirmPassword) {
    registerFormRef.value?.validateField('confirmPassword').catch(() => {})
  }
}

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
</script>
```

**数据流：** `confirmPassword` 只参与前端校验，`registerApi` 的对象里没有它；`is_superuser=False` 由服务端写死，即使请求 JSON 里带 `is_superuser: true` 也不会进入 `UserCreate` 的创建语句。

**验证：** 两次密码不一致前端拦截；重复用户名/邮箱报 400；`/docs` 里故意加 `is_superuser: true`，返回的 `data.is_superuser` 仍为 `false`。

## 第 10 节：开发文件上传 API

**知识点清单：** `UploadFile = File(...)` + 登录依赖、`FormData` 传 `multipart/form-data`、有界读取 `MAX_IMAGE_SIZE + 1`、MIME 与文件头双重校验、随机 UUID 文件名、`StaticFiles` 挂载 `/uploads`、`el-upload` 手动上传。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 格式/大小/文件头识别 | [`backend/app/api/upload.py`](../../backend/app/api/upload.py) | `ALLOWED_IMAGE_TYPES`、`MAX_IMAGE_SIZE`、`detect_image_suffix` |
| 上传接口 | 同文件 | `upload_image()` |
| 静态挂载 | [`backend/app/main.py`](../../backend/app/main.py) | `app.mount("/uploads", ...)`（第 04 节已贴） |
| FormData 封装 | [`fronted/src/api/user.js`](../../fronted/src/api/user.js) | `uploadImageApi` |
| 手动上传控件 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `el-upload` + `handleUploadChange`（完整页见文末附录） |

**完整源码：**

[`backend/app/api/upload.py`](../../backend/app/api/upload.py)（当前完整内容）：

```python
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["文件上传"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def detect_image_suffix(content: bytes) -> str | None:
    """根据文件内容识别图片类型，不能只相信客户端声明的 MIME。

    这里检查三种格式最关键的文件头/尾标记，足以拦截把脚本或文本伪装成图片的
    常见情况。正式图片处理服务还可以再用 Pillow 解码并重新编码一次。
    """
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


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """上传图片并返回静态访问地址，限制类型和 5MB 大小。"""
    declared_suffix = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not declared_suffix:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="只支持 JPG、PNG、WEBP 图片",
        )

    content = await file.read(MAX_IMAGE_SIZE + 1)
    await file.close()
    if len(content) > MAX_IMAGE_SIZE:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="图片大小不能超过 5MB")

    detected_suffix = detect_image_suffix(content)
    if not detected_suffix or detected_suffix != declared_suffix:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="图片内容与文件类型不匹配",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{detected_suffix}"
    (UPLOAD_DIR / filename).write_bytes(content)
    return Response.success(
        message="上传成功",
        data={"filename": filename, "url": f"/uploads/{filename}"},
    )
```

[`fronted/src/api/user.js`](../../fronted/src/api/user.js)（当前完整内容；本文件被第 10–14 节共用）：

```js
import request from '@/utils/request'

export function getUserInfoApi() {
  return request.get('/api/user/info')
}

export function updateProfileApi(data) {
  return request.put('/api/user/profile', data)
}

export function updatePasswordApi(data) {
  return request.put('/api/user/password', data)
}

export function getUserListApi(params) {
  return request.get('/api/user', { params })
}

export function createUserApi(data) {
  return request.post('/api/user', data)
}

export function updateUserApi(userId, data) {
  return request.put(`/api/user/${userId}`, data)
}

export function deleteUserApi(userId) {
  return request.delete(`/api/user/${userId}`)
}

export function uploadImageApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/upload/image', formData)
}
```

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中与上传相关的片段（完整页面见文末附录）：

```vue
<el-upload :auto-upload="false" :show-file-list="false" accept="image/jpeg,image/png,image/webp" :on-change="handleUploadChange">
  <el-button :loading="uploadingValue">选择并上传图片</el-button>
</el-upload>
<img v-if="uploadedImageUrl" :src="uploadedImageUrl" alt="上传预览" />
<span v-else>支持 JPG、PNG、WEBP，最大 5MB</span>
```

```js
const handleUploadChange = async (uploadFile) => {
  if (!uploadFile.raw) return
  uploadingValue.value = true
  try {
    const res = await uploadImageApi(uploadFile.raw)
    uploadedImageUrl.value = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}${res.data.url}`
    ElMessage.success('图片上传成功')
  } finally { uploadingValue.value = false }
}
```

**数据流：** `el-upload` 的 `uploadFile.raw` 是浏览器 `File` → `FormData` 字段名 `file`（与后端参数同名）→ 后端校验后生成 `filename` 和相对 `url` → 前端拼 API 地址预览。刷新页面后预览消失，因为当前**没有** `avatar_url` 字段和保存接口，“上传成功”不等于“头像已持久化”。

**验证：** 上传真实 PNG/JPEG/WEBP 能看到预览；`/docs` 传改名为 `.png` 的文本文件被拒；无 Token 返回 401。

## 第 11 节：修改个人信息与共享用户状态

**知识点清单：** `GET /api/user/info` 读当前用户、`PUT /api/user/profile` 只改姓名邮箱、邮箱占用检查排除自己、`current_user` 由依赖注入而非请求体、响应式共享 `userInfo`。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 读取/修改接口 | [`backend/app/api/user.py`](../../backend/app/api/user.py) | `get_user_info`、`update_profile` |
| 输入模型 | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `UserProfileUpdate`（第 09 节已贴） |
| 共享用户状态 | [`fronted/src/utils/user.js`](../../fronted/src/utils/user.js) | `useUser`（第 03 节已贴完整） |
| 个人资料表单 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `saveProfile`（完整页见附录） |

**完整源码：**

[`backend/app/api/user.py`](../../backend/app/api/user.py)（当前完整内容；本文件同时被第 12–14 节复用）：

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.user import User
from app.schemas.user import (
    AdminUserCreate,
    AdminUserUpdate,
    UserPasswordUpdate,
    UserProfileUpdate,
    UserResponse,
)
from app.utils.password import hash_password, verify_password

router = APIRouter(prefix="/user", tags=["用户信息接口"])


@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息，前端刷新页面后可用它恢复登录状态。"""
    return Response.success(data=UserResponse.model_validate(current_user))


@router.put("/profile")
def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户修改自己的姓名与邮箱。"""
    email = str(data.email).lower()
    email_owner = db.query(User).filter(User.email == email, User.id != current_user.id).first()
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


@router.put("/password")
def update_password(
    data: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码前再次校验旧密码，避免登录会话被盗后直接改密。"""
    if not verify_password(data.old_password, current_user.password):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="原密码不正确")
    if data.old_password == data.new_password:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="新密码不能与原密码相同")

    current_user.password = hash_password(data.new_password)
    db.commit()
    return Response.success(message="密码修改成功，请重新登录")


@router.get("")
def get_user_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str = "",
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员分页查询用户；用户名、姓名和邮箱都支持模糊搜索。"""
    query = db.query(User)
    if keyword.strip():
        search_value = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                User.username.like(search_value),
                User.full_name.like(search_value),
                User.email.like(search_value),
            )
        )

    total = query.count()
    users = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Response.success(
        data={
            "list": [UserResponse.model_validate(user) for user in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("")
def create_user(
    data: AdminUserCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员新增普通用户或管理员账号。"""
    username = data.username.strip()
    email = str(data.email).lower()
    if db.query(User).filter(or_(User.username == username, User.email == email)).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="用户名或邮箱已存在")

    user = User(
        username=username,
        password=hash_password(data.password),
        email=email,
        full_name=data.full_name.strip() if data.full_name else None,
        is_active=data.is_active,
        is_superuser=data.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return Response.success(message="用户新增成功", data=UserResponse.model_validate(user))


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员修改账号资料、角色和启用状态。"""
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
        exists = db.query(User).filter(User.email == update_data["email"], User.id != user_id).first()
        if exists:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="邮箱已被其他账号使用")
    if update_data.get("full_name"):
        update_data["full_name"] = update_data["full_name"].strip()

    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return Response.success(message="用户修改成功", data=UserResponse.model_validate(user))


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除用户。已产生预约记录的用户应优先禁用，数据库会阻止误删。"""
    if user_id == current_admin.id:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="不能删除当前登录账号")
    user = db.get(User, user_id)
    if not user:
        raise BusinessException(code=BizCode.NOT_FOUND, message="用户不存在")

    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="该用户已有业务数据，请改为禁用账号",
        )
    return Response.success(message="用户删除成功")
```

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中个人资料部分（完整页见附录）：

```vue
<el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="90px" class="narrow-form">
  <el-form-item label="用户名"><el-input :model-value="userInfo?.username" disabled /></el-form-item>
  <el-form-item label="姓名" prop="full_name"><el-input v-model="profileForm.full_name" placeholder="请输入姓名" /></el-form-item>
  <el-form-item label="邮箱" prop="email"><el-input v-model="profileForm.email" placeholder="请输入邮箱" /></el-form-item>
  <el-form-item label="账号角色"><el-tag :type="isAdmin ? 'danger' : 'success'">{{ isAdmin ? '管理员' : '普通用户' }}</el-tag></el-form-item>
  <el-form-item><el-button type="primary" :loading="savingValue" @click="saveProfile">保存个人信息</el-button></el-form-item>
</el-form>
```

```js
const profileForm = reactive({ full_name: '', email: '' })
const profileRules = { email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }] }

const saveProfile = async () => {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const res = await updateProfileApi({ email: profileForm.email.trim(), full_name: profileForm.full_name.trim() || null })
    updateUser(res.data)
    ElMessage.success('个人信息修改成功')
  } finally { savingValue.value = false }
}
```

**数据流：** `request.js` 自动加 Bearer → `get_current_user` 得到当前用户 → 接口不接收 `user_id` → 邮箱检查 `User.id != current_user.id` 避免误报 → `updateUser(res.data)` 同时更新本地缓存和共享状态。

**验证：** 改姓名/邮箱后页面与接口一致、刷新保持；改成他人已占用邮箱得 400；请求体里塞 `user_id` 不会改变修改目标。

## 第 12 节：修改密码与旧 Token 失效

**知识点清单：** 验证旧密码、拒绝新旧相同、存新 bcrypt 哈希、`password_version` 让旧 Token 失效、前端改密后清本地凭证并回登录页。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 改密接口 | [`backend/app/api/user.py`](../../backend/app/api/user.py) | `update_password`（第 11 节已贴完整） |
| 输入模型 | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `UserPasswordUpdate`（第 09 节已贴） |
| 密码版本 | [`backend/app/utils/jwt.py`](../../backend/app/utils/jwt.py) + [`backend/app/dependencies/auth.py`](../../backend/app/dependencies/auth.py) | 第 06 节已贴完整 |
| 前端改密表单 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `savePassword`（完整页见附录） |

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中改密部分：

```js
const passwordForm = reactive({ old_password: '', new_password: '', confirmPassword: '' })
const validateNewPassword = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入新密码'))
  else if (value !== passwordForm.new_password) callback(new Error('两次输入的密码不一致'))
  else callback()
}
const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 8, max: 64, message: '密码长度为 8～64 个字符', trigger: 'blur' }],
  confirmPassword: [{ validator: validateNewPassword, trigger: 'blur' }]
}

const savePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await updatePasswordApi({ old_password: passwordForm.old_password, new_password: passwordForm.new_password })
    ElMessage.success('密码修改成功，请重新登录')
    clearLoginData()
    await router.replace('/login')
  } finally { savingValue.value = false }
}
```

**数据流：** 前端校验两次输入 → `updatePasswordApi` 发旧/新密码 → 后端验证旧密码 → 存新哈希 → 旧 JWT 的 `password_version` 失配 → 前端 `clearLoginData()` 并跳登录。

**验证：** 错误旧密码/新旧相同报 400；改密后旧 Token 请求 `/api/user/info` 返回 401，新密码重新登录成功。此操作真实改密，只对自己的练习账号执行。

## 第 13 节：管理员用户列表

**知识点清单：** `get_current_admin` 授权、`Query(ge/le)` 限制页码、`or_` 多字段模糊搜索、`count()` 总数 + `offset/limit` 分页、axios `params` 拼查询串、`el-table` + `el-pagination` 共享状态。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 列表接口 | [`backend/app/api/user.py`](../../backend/app/api/user.py) | `get_user_list`（第 11 节已贴完整） |
| 管理员授权 | [`backend/app/dependencies/permission.py`](../../backend/app/dependencies/permission.py) | `get_current_admin`（第 06 节已贴完整） |
| 列表 API | [`fronted/src/api/user.js`](../../fronted/src/api/user.js) | `getUserListApi`（第 10 节已贴完整） |
| 表格与分页 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `searchParams`、`loadUserList`（完整页见附录） |

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中列表部分（模板 + 逻辑）：

```vue
<el-tab-pane v-if="isAdmin" label="用户管理" name="manager">
  <div class="toolbar">
    <el-input v-model="searchParams.keyword" clearable placeholder="用户名、姓名或邮箱" style="width: 240px" @keyup.enter="loadUserList" @clear="loadUserList" />
    <el-button @click="loadUserList">查询</el-button>
    <el-button type="primary" @click="openUserDialog()">新增用户</el-button>
  </div>
  <el-table v-loading="loadingValue" :data="userList" stripe>
    <el-table-column prop="username" label="用户名" min-width="110" />
    <el-table-column prop="full_name" label="姓名" min-width="100" />
    <el-table-column prop="email" label="邮箱" min-width="190" />
    <el-table-column label="角色" width="100"><template #default="scope"><el-tag :type="scope.row.is_superuser ? 'danger' : 'success'">{{ scope.row.is_superuser ? '管理员' : '用户' }}</el-tag></template></el-table-column>
    <el-table-column label="状态" width="90"><template #default="scope"><el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '禁用' }}</el-tag></template></el-table-column>
    <el-table-column label="注册时间" min-width="170"><template #default="scope">{{ formatDate(scope.row.create_time) }}</template></el-table-column>
    <el-table-column label="操作" width="140" fixed="right"><template #default="scope"><el-button link type="primary" @click="openUserDialog(scope.row)">编辑</el-button><el-button link type="danger" @click="removeUser(scope.row)">删除</el-button></template></el-table-column>
  </el-table>
  <el-pagination v-model:current-page="searchParams.page" v-model:page-size="searchParams.page_size" layout="total, prev, pager, next" :total="userTotal" class="pagination" @current-change="loadUserList" />
</el-tab-pane>
```

```js
const userList = ref([])
const userTotal = ref(0)
const searchParams = reactive({ page: 1, page_size: 10, keyword: '' })

const loadUserList = async () => {
  loadingValue.value = true
  try {
    const res = await getUserListApi(searchParams)
    userList.value = res.data.list
    userTotal.value = res.data.total
  } finally { loadingValue.value = false }
}
```

**数据流：** `searchParams` 变化 → `getUserListApi` 把参数变成 URL 查询串 → 后端先授权再查总数和当前页 → `res.data.list` 驱动表格、`res.data.total` 驱动分页。

**验证：** 管理员按用户名/姓名/邮箱搜索、翻页，观察 Network 查询参数；普通用户 Token 请求 `GET /api/user` 得 403，不带 Token 得 401。

## 第 14 节：管理员用户增删改

**知识点清单：** `AdminUserCreate/AdminUserUpdate` 分建模、`model_dump(exclude_unset=True)` 局部更新、`model_fields_set` 区分“没传”与“传 null”、自我保护（不能禁用/降权/删除自己）、`IntegrityError` 兜底外键约束、对话框新增/编辑双模式。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 增删改接口 | [`backend/app/api/user.py`](../../backend/app/api/user.py) | `create_user`、`update_user`、`delete_user`（第 11 节已贴完整） |
| 增删改 Schema | [`backend/app/schemas/user.py`](../../backend/app/schemas/user.py) | `AdminUserCreate`、`AdminUserUpdate`（第 09 节已贴完整） |
| 增删改 API | [`fronted/src/api/user.js`](../../fronted/src/api/user.js) | `createUserApi`、`updateUserApi`、`deleteUserApi`（第 10 节已贴完整） |
| 对话框双模式 | [`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) | `openUserDialog`、`saveUser`、`removeUser`（完整页见附录） |

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue) 中新增/编辑对话框模板：

```vue
<el-dialog v-model="userDialogVisible" :title="userForm.id ? '编辑用户' : '新增用户'" width="520px">
  <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
    <el-form-item label="用户名" prop="username"><el-input v-model="userForm.username" :disabled="Boolean(userForm.id)" /></el-form-item>
    <el-form-item v-if="!userForm.id" label="初始密码" prop="password"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
    <el-form-item label="姓名"><el-input v-model="userForm.full_name" /></el-form-item>
    <el-form-item label="邮箱" prop="email"><el-input v-model="userForm.email" /></el-form-item>
    <el-form-item label="管理员"><el-switch v-model="userForm.is_superuser" /></el-form-item>
    <el-form-item label="启用账号"><el-switch v-model="userForm.is_active" /></el-form-item>
  </el-form>
  <template #footer><el-button @click="userDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveUser">保存</el-button></template>
</el-dialog>
```

```js
const openUserDialog = (user = null) => {
  Object.assign(userForm, user ? { ...user, password: '' } : { id: null, username: '', password: '', full_name: '', email: '', is_active: true, is_superuser: false })
  userDialogVisible.value = true
}

const saveUser = async () => {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    if (userForm.id) {
      await updateUserApi(userForm.id, { email: userForm.email.trim(), full_name: userForm.full_name?.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser })
    } else {
      await createUserApi({ username: userForm.username.trim(), password: userForm.password, email: userForm.email.trim(), full_name: userForm.full_name.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser })
    }
    ElMessage.success(userForm.id ? '用户修改成功' : '用户新增成功')
    userDialogVisible.value = false
    await loadUserList()
  } finally { savingValue.value = false }
}

const removeUser = async (user) => {
  try {
    await ElMessageBox.confirm(`确定删除用户“${user.username}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // Element Plus 在用户取消或关闭确认框时会 reject，这是正常操作，直接结束即可。
    return
  }
  await deleteUserApi(user.id)
  ElMessage.success('删除成功')
  await loadUserList()
}
```

**数据流：** 打开对话框 → 表单校验 → POST 或 PUT → 后端校验身份/字段 → ORM `commit()` → 前端 `loadUserList()` 刷新。编辑时 `v-if="!userForm.id"` 使初始密码只在新增出现，编辑提交对象不含 `username/password`。

**验证：** 新增可搜索、编辑后刷新正确；编辑自己尝试禁用/降权得 400；取消删除确认框时 Network 无 DELETE；删除有预约记录的用户会因外键约束失败，改为禁用。

## 本组自检

用一张流程图串起 `UserCreate/AdminUserCreate → auth/user 路由 → get_current_user/get_current_admin → User ORM → UserResponse → src/api/user.js → user.vue`。解释三类数据去向：密码明文只短暂存在于请求、数据库存 bcrypt 哈希、响应不含密码。再回答：注册为什么不能指定管理员？上传为什么刷新后没有头像？改密为什么旧 Token 失效？前端隐藏管理页与接口权限有什么不同？

---

## 附录：`user.vue` 完整源码（本组第 10–14 节共用页面）

[`fronted/src/views/user.vue`](../../fronted/src/views/user.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 为纯 CSS 表现，省略）：

```vue
<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">{{ isAdmin ? '用户与个人中心' : '个人中心' }}</h1></div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="个人信息" name="profile">
        <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="90px" class="narrow-form">
          <el-form-item label="用户名"><el-input :model-value="userInfo?.username" disabled /></el-form-item>
          <el-form-item label="姓名" prop="full_name"><el-input v-model="profileForm.full_name" placeholder="请输入姓名" /></el-form-item>
          <el-form-item label="邮箱" prop="email"><el-input v-model="profileForm.email" placeholder="请输入邮箱" /></el-form-item>
          <el-form-item label="账号角色"><el-tag :type="isAdmin ? 'danger' : 'success'">{{ isAdmin ? '管理员' : '普通用户' }}</el-tag></el-form-item>
          <el-form-item><el-button type="primary" :loading="savingValue" @click="saveProfile">保存个人信息</el-button></el-form-item>
        </el-form>

        <el-divider content-position="left">文件上传接口演示</el-divider>
        <div class="upload-demo">
          <el-upload :auto-upload="false" :show-file-list="false" accept="image/jpeg,image/png,image/webp" :on-change="handleUploadChange">
            <el-button :loading="uploadingValue">选择并上传图片</el-button>
          </el-upload>
          <img v-if="uploadedImageUrl" :src="uploadedImageUrl" alt="上传预览" />
          <span v-else>支持 JPG、PNG、WEBP，最大 5MB</span>
        </div>
      </el-tab-pane>

      <el-tab-pane label="修改密码" name="password">
        <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px" class="narrow-form">
          <el-form-item label="原密码" prop="old_password"><el-input v-model="passwordForm.old_password" type="password" show-password /></el-form-item>
          <el-form-item label="新密码" prop="new_password"><el-input v-model="passwordForm.new_password" type="password" show-password /></el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword"><el-input v-model="passwordForm.confirmPassword" type="password" show-password /></el-form-item>
          <el-form-item><el-button type="primary" :loading="savingValue" @click="savePassword">修改密码</el-button></el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane v-if="isAdmin" label="用户管理" name="manager">
        <div class="toolbar">
          <el-input v-model="searchParams.keyword" clearable placeholder="用户名、姓名或邮箱" style="width: 240px" @keyup.enter="loadUserList" @clear="loadUserList" />
          <el-button @click="loadUserList">查询</el-button>
          <el-button type="primary" @click="openUserDialog()">新增用户</el-button>
        </div>
        <el-table v-loading="loadingValue" :data="userList" stripe>
          <el-table-column prop="username" label="用户名" min-width="110" />
          <el-table-column prop="full_name" label="姓名" min-width="100" />
          <el-table-column prop="email" label="邮箱" min-width="190" />
          <el-table-column label="角色" width="100"><template #default="scope"><el-tag :type="scope.row.is_superuser ? 'danger' : 'success'">{{ scope.row.is_superuser ? '管理员' : '用户' }}</el-tag></template></el-table-column>
          <el-table-column label="状态" width="90"><template #default="scope"><el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '禁用' }}</el-tag></template></el-table-column>
          <el-table-column label="注册时间" min-width="170"><template #default="scope">{{ formatDate(scope.row.create_time) }}</template></el-table-column>
          <el-table-column label="操作" width="140" fixed="right"><template #default="scope"><el-button link type="primary" @click="openUserDialog(scope.row)">编辑</el-button><el-button link type="danger" @click="removeUser(scope.row)">删除</el-button></template></el-table-column>
        </el-table>
        <el-pagination v-model:current-page="searchParams.page" v-model:page-size="searchParams.page_size" layout="total, prev, pager, next" :total="userTotal" class="pagination" @current-change="loadUserList" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="userDialogVisible" :title="userForm.id ? '编辑用户' : '新增用户'" width="520px">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-form-item label="用户名" prop="username"><el-input v-model="userForm.username" :disabled="Boolean(userForm.id)" /></el-form-item>
        <el-form-item v-if="!userForm.id" label="初始密码" prop="password"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="userForm.full_name" /></el-form-item>
        <el-form-item label="邮箱" prop="email"><el-input v-model="userForm.email" /></el-form-item>
        <el-form-item label="管理员"><el-switch v-model="userForm.is_superuser" /></el-form-item>
        <el-form-item label="启用账号"><el-switch v-model="userForm.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="userDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveUser">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { createUserApi, deleteUserApi, getUserListApi, updatePasswordApi, updateProfileApi, updateUserApi, uploadImageApi } from '@/api/user'
import { useUser } from '@/utils/user'

const router = useRouter()
const { userInfo, isAdmin, updateUser, clearLoginData } = useUser()
const activeTab = ref('profile')
const loadingValue = ref(false)
const savingValue = ref(false)
const uploadingValue = ref(false)
const uploadedImageUrl = ref('')
const userDialogVisible = ref(false)
const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const userFormRef = ref(null)
const userList = ref([])
const userTotal = ref(0)

const profileForm = reactive({ full_name: '', email: '' })
const passwordForm = reactive({ old_password: '', new_password: '', confirmPassword: '' })
const searchParams = reactive({ page: 1, page_size: 10, keyword: '' })
const userForm = reactive({ id: null, username: '', password: '', full_name: '', email: '', is_active: true, is_superuser: false })

const profileRules = { email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }] }
const validateNewPassword = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入新密码'))
  else if (value !== passwordForm.new_password) callback(new Error('两次输入的密码不一致'))
  else callback()
}
const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 8, max: 64, message: '密码长度为 8～64 个字符', trigger: 'blur' }],
  confirmPassword: [{ validator: validateNewPassword, trigger: 'blur' }]
}
const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, max: 20, message: '长度为 3～20 个字符', trigger: 'blur' }],
  password: [{ required: true, message: '请输入初始密码', trigger: 'blur' }, { min: 8, max: 64, message: '长度为 8～64 个字符', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }]
}

const saveProfile = async () => {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const res = await updateProfileApi({ email: profileForm.email.trim(), full_name: profileForm.full_name.trim() || null })
    updateUser(res.data)
    ElMessage.success('个人信息修改成功')
  } finally { savingValue.value = false }
}

const savePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await updatePasswordApi({ old_password: passwordForm.old_password, new_password: passwordForm.new_password })
    ElMessage.success('密码修改成功，请重新登录')
    clearLoginData()
    await router.replace('/login')
  } finally { savingValue.value = false }
}

const handleUploadChange = async (uploadFile) => {
  if (!uploadFile.raw) return
  uploadingValue.value = true
  try {
    const res = await uploadImageApi(uploadFile.raw)
    uploadedImageUrl.value = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}${res.data.url}`
    ElMessage.success('图片上传成功')
  } finally { uploadingValue.value = false }
}

const loadUserList = async () => {
  loadingValue.value = true
  try {
    const res = await getUserListApi(searchParams)
    userList.value = res.data.list
    userTotal.value = res.data.total
  } finally { loadingValue.value = false }
}

const openUserDialog = (user = null) => {
  Object.assign(userForm, user ? { ...user, password: '' } : { id: null, username: '', password: '', full_name: '', email: '', is_active: true, is_superuser: false })
  userDialogVisible.value = true
}

const saveUser = async () => {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    if (userForm.id) {
      await updateUserApi(userForm.id, { email: userForm.email.trim(), full_name: userForm.full_name?.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser })
    } else {
      await createUserApi({ username: userForm.username.trim(), password: userForm.password, email: userForm.email.trim(), full_name: userForm.full_name.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser })
    }
    ElMessage.success(userForm.id ? '用户修改成功' : '用户新增成功')
    userDialogVisible.value = false
    await loadUserList()
  } finally { savingValue.value = false }
}

const removeUser = async (user) => {
  try {
    await ElMessageBox.confirm(`确定删除用户“${user.username}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // Element Plus 在用户取消或关闭确认框时会 reject，这是正常操作，直接结束即可。
    return
  }
  await deleteUserApi(user.id)
  ElMessage.success('删除成功')
  await loadUserList()
}

const formatDate = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'

onMounted(async () => {
  Object.assign(profileForm, { full_name: userInfo.value?.full_name || '', email: userInfo.value?.email || '' })
  if (isAdmin.value) await loadUserList()
})
</script>
```


---

# 第三部分：实验室、设备与预约业务

## 第 15 节：开发实验室管理功能

**知识点清单：** `Lab` ORM 实体与字段约束、`LabCreate/LabUpdate/LabResponse` 区分输入输出、`field_validator` 去空白、`model_validator` 拒绝把必填列设为 null、管理员增删改 / 登录用户查询、`status=1/0` 开放与暂停、`only_open` 查询过滤、外键约束导致删除受限、前端 `el-table` + 对话框表单。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 数据表与状态字段 | [`backend/app/models/lab.py`](../../backend/app/models/lab.py) | `class Lab(Base)`、`status` |
| 输入/输出模型 | [`backend/app/schemas/lab.py`](../../backend/app/schemas/lab.py) | `LabBase/LabCreate/LabUpdate/LabResponse` |
| 查询与增删改 | [`backend/app/api/lab.py`](../../backend/app/api/lab.py) | `get_lab_list/create_lab/update_lab/delete_lab` |
| 前端接口 | [`fronted/src/api/lab.js`](../../fronted/src/api/lab.js) | 四个 API 函数 |
| 实验室页面 | [`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue) | 完整组件（见下） |

**完整源码：**

[`backend/app/models/lab.py`](../../backend/app/models/lab.py)（当前完整内容）：

```python
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lab(Base):
    """实验室基础信息。"""

    __tablename__ = "labs"
    __table_args__ = {"comment": "实验室表"}

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 1 表示开放预约，0 表示暂停使用。
    status: Mapped[int] = mapped_column(default=1, nullable=False)
```

[`backend/app/schemas/lab.py`](../../backend/app/schemas/lab.py)（当前完整内容）：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LabBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=200)
    capacity: int = Field(default=1, ge=1, le=1000)
    description: str | None = None
    status: int = Field(default=1, ge=0, le=1)

    @field_validator("name", "location")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """先去掉两端空格，再检查真正可见的字符数。"""
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned


class LabCreate(LabBase):
    pass


class LabUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    location: str | None = Field(default=None, min_length=2, max_length=200)
    capacity: int | None = Field(default=None, ge=1, le=1000)
    description: str | None = None
    status: int | None = Field(default=None, ge=0, le=1)

    @field_validator("name", "location")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        # PATCH 风格更新允许省略字段，但不能把数据库里的必填列显式改成 null。
        required_fields = ("name", "location", "capacity", "status")
        if any(field in self.model_fields_set and getattr(self, field) is None for field in required_fields):
            raise ValueError("实验室必填字段不能设为 null")
        return self


class LabResponse(LabBase):
    id: int
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

[`backend/app/api/lab.py`](../../backend/app/api/lab.py)（当前完整内容）：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.lab import Lab
from app.models.user import User
from app.schemas.lab import LabCreate, LabResponse, LabUpdate

router = APIRouter(prefix="/labs", tags=["实验室管理"])


@router.get("")
def get_lab_list(
    keyword: str = "",
    only_open: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询实验室列表；学生端通过 only_open 只展示开放实验室。"""
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


@router.put("/{lab_id}")
def update_lab(
    lab_id: int,
    data: LabUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lab = db.get(Lab, lab_id)
    if not lab:
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("name"):
        update_data["name"] = update_data["name"].strip()
        exists = db.query(Lab).filter(Lab.name == update_data["name"], Lab.id != lab_id).first()
        if exists:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室名称已存在")
    for field, value in update_data.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return Response.success(message="实验室修改成功", data=LabResponse.model_validate(lab))


@router.delete("/{lab_id}")
def delete_lab(
    lab_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lab = db.get(Lab, lab_id)
    if not lab:
        raise BusinessException(code=BizCode.NOT_FOUND, message="实验室不存在")
    db.delete(lab)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="实验室已有设备或预约记录，请改为暂停开放",
        )
    return Response.success(message="实验室删除成功")
```

[`fronted/src/api/lab.js`](../../fronted/src/api/lab.js)（当前完整内容；被第 15、17、18、19 节共用）：

```js
import request from '@/utils/request'

export function getLabListApi(params) {
  return request.get('/api/labs', { params })
}

export function createLabApi(data) {
  return request.post('/api/labs', data)
}

export function updateLabApi(labId, data) {
  return request.put(`/api/labs/${labId}`, data)
}

export function deleteLabApi(labId) {
  return request.delete(`/api/labs/${labId}`)
}
```

[`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 只有一行对话框间距，省略）：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '实验室管理' : '可预约实验室' }}</h1>
      <el-button v-if="isAdmin" type="primary" @click="openLabDialog()">新增实验室</el-button>
    </div>
    <div class="toolbar">
      <el-input v-model="keyword" clearable placeholder="搜索实验室名称" style="width: 240px" @keyup.enter="loadLabList" @clear="loadLabList" />
      <el-button @click="loadLabList">查询</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="labList" stripe>
      <el-table-column prop="name" label="实验室名称" min-width="150" />
      <el-table-column prop="location" label="位置" min-width="160" />
      <el-table-column prop="capacity" label="容纳人数" width="100" />
      <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="scope.row.status === 1 ? 'success' : 'info'">{{ scope.row.status === 1 ? '开放' : '暂停' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" :width="isAdmin ? 250 : 180" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="showEquipment(scope.row)">查看设备</el-button>
          <template v-if="isAdmin">
            <el-button link type="primary" @click="openLabDialog(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="removeLab(scope.row)">删除</el-button>
          </template>
          <el-button v-else link type="success" @click="openReservationDialog(scope.row)">立即预约</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="labDialogVisible" :title="labForm.id ? '编辑实验室' : '新增实验室'" width="520px">
      <el-form ref="labFormRef" :model="labForm" :rules="labRules" label-width="90px">
        <el-form-item label="名称" prop="name"><el-input v-model="labForm.name" /></el-form-item>
        <el-form-item label="位置" prop="location"><el-input v-model="labForm.location" /></el-form-item>
        <el-form-item label="容纳人数" prop="capacity"><el-input-number v-model="labForm.capacity" :min="1" :max="1000" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="labForm.status" :active-value="1" :inactive-value="0" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="labForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="labDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveLab">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="reservationDialogVisible" title="提交实验室预约" width="520px">
      <el-alert :title="`正在预约：${selectedLab?.name || ''}`" type="info" :closable="false" />
      <el-form ref="reservationFormRef" :model="reservationForm" :rules="reservationRules" label-width="90px" class="dialog-form">
        <el-form-item label="预约日期" prop="reservation_date"><el-date-picker v-model="reservationForm.reservation_date" type="date" value-format="YYYY-MM-DD" :disabled-date="disablePastDate" style="width: 100%" /></el-form-item>
        <el-form-item label="预约时间" prop="timeRange"><el-time-picker v-model="reservationForm.timeRange" is-range value-format="HH:mm:ss" range-separator="至" start-placeholder="开始时间" end-placeholder="结束时间" style="width: 100%" /></el-form-item>
        <el-form-item label="预约用途" prop="purpose"><el-input v-model="reservationForm.purpose" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="reservationDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveReservation">提交申请</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { createLabApi, deleteLabApi, getLabListApi, updateLabApi } from '@/api/lab'
import { createReservationApi } from '@/api/reservation'
import { useUser } from '@/utils/user'

const router = useRouter()
const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const keyword = ref('')
const labList = ref([])
const labDialogVisible = ref(false)
const reservationDialogVisible = ref(false)
const labFormRef = ref(null)
const reservationFormRef = ref(null)
const selectedLab = ref(null)
const labForm = reactive({ id: null, name: '', location: '', capacity: 1, description: '', status: 1 })
const reservationForm = reactive({ reservation_date: '', timeRange: [], purpose: '' })

const labRules = {
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  location: [{ required: true, message: '请输入实验室位置', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容纳人数', trigger: 'change' }]
}
const reservationRules = {
  reservation_date: [{ required: true, message: '请选择预约日期', trigger: 'change' }],
  timeRange: [{ type: 'array', required: true, len: 2, message: '请选择预约时间', trigger: 'change' }],
  purpose: [{ required: true, message: '请填写预约用途', trigger: 'blur' }]
}

const loadLabList = async () => {
  loadingValue.value = true
  try {
    const res = await getLabListApi({ keyword: keyword.value, only_open: !isAdmin.value })
    labList.value = res.data
  } finally { loadingValue.value = false }
}

const openLabDialog = (lab = null) => {
  Object.assign(labForm, lab || { id: null, name: '', location: '', capacity: 1, description: '', status: 1 })
  labDialogVisible.value = true
}

const saveLab = async () => {
  const valid = await labFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = { name: labForm.name.trim(), location: labForm.location.trim(), capacity: labForm.capacity, description: labForm.description || null, status: labForm.status }
    if (labForm.id) await updateLabApi(labForm.id, data)
    else await createLabApi(data)
    ElMessage.success(labForm.id ? '实验室修改成功' : '实验室新增成功')
    labDialogVisible.value = false
    await loadLabList()
  } finally { savingValue.value = false }
}

const removeLab = async (lab) => {
  try {
    await ElMessageBox.confirm(`确定删除“${lab.name}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // 取消确认框属于正常分支，不应继续删除，也不向 Vue 抛出未处理异常。
    return
  }
  await deleteLabApi(lab.id)
  ElMessage.success('删除成功')
  await loadLabList()
}

const showEquipment = (lab) => router.push({ path: '/equ', query: { lab_id: lab.id } })
const openReservationDialog = (lab) => {
  selectedLab.value = lab
  Object.assign(reservationForm, { reservation_date: '', timeRange: [], purpose: '' })
  reservationDialogVisible.value = true
}
const disablePastDate = (date) => date.getTime() < new Date().setHours(0, 0, 0, 0)

const saveReservation = async () => {
  const valid = await reservationFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await createReservationApi({ lab_id: selectedLab.value.id, reservation_date: reservationForm.reservation_date, start_time: reservationForm.timeRange[0], end_time: reservationForm.timeRange[1], purpose: reservationForm.purpose.trim() })
    ElMessage.success('预约申请已提交')
    reservationDialogVisible.value = false
    await router.push('/reservation')
  } finally { savingValue.value = false }
}

onMounted(loadLabList)
</script>
```

**数据流：** 学生页面默认 `only_open: !isAdmin` → 后端按 `Lab.status == 1` 过滤；管理员 `only_open=false` 能看到暂停的实验室。`only_open` 是查询选项，不是学生端的强制数据权限。

**验证：** 管理员新增/改容量/暂停开放；学生默认看不到暂停实验室。删除有设备或预约的实验室会因外键约束返回 400，应改为暂停开放。

## 第 16 节：开发实验室设备管理

**知识点清单：** `lab_id` 外键归属实验室、`relationship("Lab")`、`joinedload(Equipment.lab)` 预加载避免 N+1、设备编号唯一、`status` + `quantity` 决定可用、`equipment_to_dict` 把关联实验室名一起返回、前端按实验室筛选。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 设备表与外键 | [`backend/app/models/equipment.py`](../../backend/app/models/equipment.py) | `lab_id = ForeignKey("labs.id")`、`lab = relationship("Lab")` |
| 输入/输出模型 | [`backend/app/schemas/equipment.py`](../../backend/app/schemas/equipment.py) | `EquipmentBase/Create/Update/Response` |
| 预加载与可用过滤 | [`backend/app/api/equipment.py`](../../backend/app/api/equipment.py) | `joinedload`、`only_available` |
| 前端接口 | [`fronted/src/api/equipment.js`](../../fronted/src/api/equipment.js) | 四个 API 函数 |
| 设备页面 | [`fronted/src/views/equ.vue`](../../fronted/src/views/equ.vue) | 完整组件（见下） |

**完整源码：**

[`backend/app/models/equipment.py`](../../backend/app/models/equipment.py)（当前完整内容）：

```python
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Equipment(Base):
    """实验室设备信息。"""

    __tablename__ = "equipment"
    __table_args__ = {"comment": "实验室设备表"}

    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 1 表示正常，0 表示停用或维护中。
    status: Mapped[int] = mapped_column(default=1, nullable=False)

    lab = relationship("Lab")
```

[`backend/app/schemas/equipment.py`](../../backend/app/schemas/equipment.py)（当前完整内容）：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EquipmentBase(BaseModel):
    lab_id: int
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=50)
    quantity: int = Field(default=1, ge=0, le=10000)
    description: str | None = None
    status: int = Field(default=1, ge=0, le=1)

    @field_validator("name", "code")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    lab_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=100)
    code: str | None = Field(default=None, min_length=2, max_length=50)
    quantity: int | None = Field(default=None, ge=0, le=10000)
    description: str | None = None
    status: int | None = Field(default=None, ge=0, le=1)

    @field_validator("name", "code")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("至少需要 2 个非空白字符")
        return cleaned

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required_fields = ("lab_id", "name", "code", "quantity", "status")
        if any(field in self.model_fields_set and getattr(self, field) is None for field in required_fields):
            raise ValueError("设备必填字段不能设为 null")
        return self


class EquipmentResponse(EquipmentBase):
    id: int
    lab_name: str | None = None
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

[`backend/app/api/equipment.py`](../../backend/app/api/equipment.py)（当前完整内容）：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.user import User
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate

router = APIRouter(prefix="/equipment", tags=["设备管理"])


def equipment_to_dict(equipment: Equipment) -> dict:
    """把关联的实验室名称一起整理给前端，避免前端再次请求。"""
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
    equipment_list = query.order_by(Equipment.id.desc()).all()
    return Response.success(data=[equipment_to_dict(item) for item in equipment_list])


@router.post("")
def create_equipment(
    data: EquipmentCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Lab, data.lab_id):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="所属实验室不存在")
    if db.query(Equipment).filter(Equipment.code == data.code.strip()).first():
        raise BusinessException(code=BizCode.BAD_REQUEST, message="设备编号已存在")
    equipment = Equipment(**data.model_dump())
    equipment.name = equipment.name.strip()
    equipment.code = equipment.code.strip()
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return Response.success(message="设备新增成功", data=equipment_to_dict(equipment))


@router.put("/{equipment_id}")
def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise BusinessException(code=BizCode.NOT_FOUND, message="设备不存在")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("lab_id") and not db.get(Lab, update_data["lab_id"]):
        raise BusinessException(code=BizCode.BAD_REQUEST, message="所属实验室不存在")
    if update_data.get("code"):
        update_data["code"] = update_data["code"].strip()
        exists = db.query(Equipment).filter(
            Equipment.code == update_data["code"], Equipment.id != equipment_id
        ).first()
        if exists:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="设备编号已存在")
    for field, value in update_data.items():
        setattr(equipment, field, value)
    db.commit()
    db.refresh(equipment)
    return Response.success(message="设备修改成功", data=equipment_to_dict(equipment))


@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise BusinessException(code=BizCode.NOT_FOUND, message="设备不存在")
    db.delete(equipment)
    db.commit()
    return Response.success(message="设备删除成功")
```

[`fronted/src/api/equipment.js`](../../fronted/src/api/equipment.js)（当前完整内容）：

```js
import request from '@/utils/request'

export function getEquipmentListApi(params) {
  return request.get('/api/equipment', { params })
}

export function createEquipmentApi(data) {
  return request.post('/api/equipment', data)
}

export function updateEquipmentApi(equipmentId, data) {
  return request.put(`/api/equipment/${equipmentId}`, data)
}

export function deleteEquipmentApi(equipmentId) {
  return request.delete(`/api/equipment/${equipmentId}`)
}
```

[`fronted/src/views/equ.vue`](../../fronted/src/views/equ.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 为空块，省略）：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '设备管理' : '实验室设备列表' }}</h1>
      <el-button v-if="isAdmin" type="primary" @click="openEquipmentDialog()">新增设备</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="selectedLabId" clearable placeholder="全部实验室" style="width: 200px" @change="loadEquipmentList">
        <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="搜索设备名称" style="width: 220px" @keyup.enter="loadEquipmentList" @clear="loadEquipmentList" />
      <el-button @click="loadEquipmentList">查询</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="equipmentList" stripe>
      <el-table-column prop="code" label="设备编号" min-width="120" />
      <el-table-column prop="name" label="设备名称" min-width="150" />
      <el-table-column prop="lab_name" label="所属实验室" min-width="150" />
      <el-table-column prop="quantity" label="数量" width="90" />
      <el-table-column prop="description" label="设备说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="scope.row.status === 1 ? 'success' : 'warning'">{{ scope.row.status === 1 ? '正常' : '维护中' }}</el-tag></template>
      </el-table-column>
      <el-table-column v-if="isAdmin" label="操作" width="150" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="openEquipmentDialog(scope.row)">编辑</el-button>
          <el-button link type="danger" @click="removeEquipment(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="equipmentForm.id ? '编辑设备' : '新增设备'" width="540px">
      <el-form ref="equipmentFormRef" :model="equipmentForm" :rules="equipmentRules" label-width="100px">
        <el-form-item label="所属实验室" prop="lab_id">
          <el-select v-model="equipmentForm.lab_id" style="width: 100%"><el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" /></el-select>
        </el-form-item>
        <el-form-item label="设备名称" prop="name"><el-input v-model="equipmentForm.name" /></el-form-item>
        <el-form-item label="设备编号" prop="code"><el-input v-model="equipmentForm.code" /></el-form-item>
        <el-form-item label="设备数量" prop="quantity"><el-input-number v-model="equipmentForm.quantity" :min="0" :max="10000" /></el-form-item>
        <el-form-item label="设备状态"><el-switch v-model="equipmentForm.status" :active-value="1" :inactive-value="0" active-text="正常" inactive-text="维护" /></el-form-item>
        <el-form-item label="设备说明"><el-input v-model="equipmentForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveEquipment">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import { createEquipmentApi, deleteEquipmentApi, getEquipmentListApi, updateEquipmentApi } from '@/api/equipment'
import { getLabListApi } from '@/api/lab'
import { useUser } from '@/utils/user'

const route = useRoute()
const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const dialogVisible = ref(false)
const equipmentFormRef = ref(null)
const labList = ref([])
const equipmentList = ref([])
const keyword = ref('')
const selectedLabId = ref(route.query.lab_id ? Number(route.query.lab_id) : null)
const equipmentForm = reactive({ id: null, lab_id: null, name: '', code: '', quantity: 1, description: '', status: 1 })

const equipmentRules = {
  lab_id: [{ required: true, message: '请选择所属实验室', trigger: 'change' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入设备编号', trigger: 'blur' }]
}

const loadLabs = async () => {
  const res = await getLabListApi()
  labList.value = res.data
}

const loadEquipmentList = async () => {
  loadingValue.value = true
  try {
    const res = await getEquipmentListApi({ lab_id: selectedLabId.value || undefined, keyword: keyword.value, only_available: !isAdmin.value })
    equipmentList.value = res.data
  } finally { loadingValue.value = false }
}

const openEquipmentDialog = (equipment = null) => {
  Object.assign(equipmentForm, equipment || { id: null, lab_id: selectedLabId.value || labList.value[0]?.id || null, name: '', code: '', quantity: 1, description: '', status: 1 })
  dialogVisible.value = true
}

const saveEquipment = async () => {
  const valid = await equipmentFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = { lab_id: equipmentForm.lab_id, name: equipmentForm.name.trim(), code: equipmentForm.code.trim(), quantity: equipmentForm.quantity, description: equipmentForm.description || null, status: equipmentForm.status }
    if (equipmentForm.id) await updateEquipmentApi(equipmentForm.id, data)
    else await createEquipmentApi(data)
    ElMessage.success(equipmentForm.id ? '设备修改成功' : '设备新增成功')
    dialogVisible.value = false
    await loadEquipmentList()
  } finally { savingValue.value = false }
}

const removeEquipment = async (equipment) => {
  try {
    await ElMessageBox.confirm(`确定删除设备“${equipment.name}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // 用户点击“取消”或关闭弹窗时，Element Plus 会 reject 这个 Promise。
    return
  }
  await deleteEquipmentApi(equipment.id)
  ElMessage.success('删除成功')
  await loadEquipmentList()
}

onMounted(async () => {
  await loadLabs()
  await loadEquipmentList()
})
</script>
```

**数据流：** `joinedload(Equipment.lab)` 一次查询就带出实验室，`equipment_to_dict` 把 `lab_name` 一起返回，列表不再逐行查库。`only_available` 同时过滤 `status == 1` 和 `quantity > 0`；注意它**只检查设备自身**，不再检查所属实验室是否开放。

**验证：** 给一个实验室加两件设备，按实验室筛选；把其中一件数量改为 0，对比管理员与学生默认列表；重复设备编号报 400。

## 第 17 节：学生端与管理端的角色渲染

**知识点清单：** 一个页面按 `isAdmin` 呈现两套操作、`v-if` 展示逻辑与后端 `get_current_admin` 写权限的区别、学生端默认 `only_open`/`only_available`、布局菜单按角色换文案。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 共享角色状态 | [`fronted/src/utils/user.js`](../../fronted/src/utils/user.js) | `isAdmin = computed(...)`（第 03 节已贴完整） |
| 菜单按角色换文案 | [`fronted/src/layouts/layouts.vue`](../../fronted/src/layouts/layouts.vue) | 第 02 节已贴完整 |
| 学生默认只查开放实验室 | [`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue) | `only_open: !isAdmin.value`（第 15 节完整） |
| 学生默认只查可用设备 | [`fronted/src/views/equ.vue`](../../fronted/src/views/equ.vue) | `only_available: !isAdmin.value`（第 16 节完整） |

**关键分支源码**（完整页面见第 15、16 节）：

```js
// views/lab.vue：学生默认只请求开放实验室
const res = await getLabListApi({ keyword: keyword.value, only_open: !isAdmin.value })
```

```js
// views/equ.vue：学生默认只请求可用设备
const res = await getEquipmentListApi({ lab_id: selectedLabId.value || undefined, keyword: keyword.value, only_available: !isAdmin.value })
```

```vue
<!-- views/lab.vue：管理员显示编辑/删除，学生显示“立即预约” -->
<template v-if="isAdmin">
  <el-button link type="primary" @click="openLabDialog(scope.row)">编辑</el-button>
  <el-button link type="danger" @click="removeLab(scope.row)">删除</el-button>
</template>
<el-button v-else link type="success" @click="openReservationDialog(scope.row)">立即预约</el-button>
```

**数据流：** `isAdmin` 来自共享 `userInfo`（登录时写入、布局 `onMounted` 又向后端确认一次）→ 决定菜单文案、按钮显隐与查询参数。但**写接口的权限由后端 `Depends(get_current_admin)` 决定**，隐藏按钮只是体验。

**验证：** 分别用学生和管理员登录，记录同一页面的标题、按钮与数据差别；用普通用户 Token 直接 `POST /api/labs`，后端仍返回 403。

## 第 18 节：开发实验室预约功能

**知识点清单：** 预约请求字段、`model_validator` 校验开始早于结束、Service 统一承担开放状态/未来时间/时间冲突/写入、半开区间冲突公式、`with_for_update()` 行锁处理并发、普通接口与 AI 工具共用同一 Service。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 预约表与状态 | [`backend/app/models/reservation.py`](../../backend/app/models/reservation.py) | `Reservation`、`status` |
| 请求模型与时间校验 | [`backend/app/schemas/reservation.py`](../../backend/app/schemas/reservation.py) | `ReservationCreate.validate_time_range` |
| 业务规则与冲突检查 | [`backend/app/services/reservation.py`](../../backend/app/services/reservation.py) | `create_reservation_record` |
| 预约接口 | [`backend/app/api/reservation.py`](../../backend/app/api/reservation.py) | `create_reservation` 等 |
| 前端接口 | [`fronted/src/api/reservation.js`](../../fronted/src/api/reservation.js) | 五个 API 函数 |
| 提交表单 | [`fronted/src/views/lab.vue`](../../fronted/src/views/lab.vue) | `saveReservation`（第 15 节完整） |

**完整源码：**

[`backend/app/models/reservation.py`](../../backend/app/models/reservation.py)（当前完整内容）：

```python
from datetime import date, time

from sqlalchemy import Date, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Reservation(Base):
    """学生提交的实验室预约申请。"""

    __tablename__ = "reservations"
    __table_args__ = {"comment": "实验室预约表"}

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"), nullable=False, index=True)
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    # pending / approved / rejected / cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    review_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user = relationship("User")
    lab = relationship("Lab")
```

[`backend/app/schemas/reservation.py`](../../backend/app/schemas/reservation.py)（当前完整内容）：

```python
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ReservationReview(BaseModel):
    status: str
    review_comment: str | None = Field(default=None, max_length=500)


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    lab_id: int
    lab_name: str
    reservation_date: date
    start_time: time
    end_time: time
    purpose: str
    status: str
    review_comment: str | None = None
    create_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

[`backend/app/services/reservation.py`](../../backend/app/services/reservation.py)（当前完整内容；普通接口与 AI 工具共用的唯一写入口）：

```python
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import BizCode
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate


def create_reservation_record(
    db: Session,
    user_id: int,
    data: ReservationCreate,
) -> Reservation:
    """创建预约的唯一业务入口，供普通接口和 AI Tool Calling 共用。

    先锁定实验室行，再检查时间冲突。MySQL/InnoDB 会让同一实验室的并发请求
    依次完成“检查 + 新增”，避免两个请求同时查到无冲突后都写入数据库。
    SQLite 测试环境会忽略 ``FOR UPDATE``，但仍可验证其余业务规则。
    """
    lab = (
        db.query(Lab)
        .filter(Lab.id == data.lab_id)
        .with_for_update()
        .first()
    )
    if not lab or lab.status != 1:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="实验室不存在或未开放",
        )
    now = datetime.now()
    if data.reservation_date < now.date():
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="不能预约过去的日期",
        )
    if data.reservation_date == now.date() and data.start_time <= now.time():
        # 日期是今天时还要检查开始时间；否则会生成无法按时使用的待审核预约。
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="预约开始时间必须晚于当前时间",
        )

    # 两个半开时间段 [start, end) 相交的充要条件：旧开始 < 新结束 且旧结束 > 新开始。
    conflict = db.query(Reservation).filter(
        Reservation.lab_id == data.lab_id,
        Reservation.reservation_date == data.reservation_date,
        Reservation.status.in_(["pending", "approved"]),
        Reservation.start_time < data.end_time,
        Reservation.end_time > data.start_time,
    ).first()
    if conflict:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="该时间段已有预约，请选择其他时间",
        )

    reservation = Reservation(
        user_id=user_id,
        status="pending",
        **data.model_dump(),
    )
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError as exc:
        # 数据库约束是最后一道保护；回滚后 Session 才能继续安全使用。
        db.rollback()
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="预约创建失败，请确认用户和实验室信息",
        ) from exc
    db.refresh(reservation)
    return reservation
```

[`backend/app/api/reservation.py`](../../backend/app/api/reservation.py)（当前完整内容；第 19 节的列表/审核也在此文件）：

```python
from fastapi import APIRouter, Depends
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permission import get_current_admin
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationReview
from app.services.reservation import create_reservation_record

router = APIRouter(prefix="/reservations", tags=["实验室预约"])


def reservation_to_dict(reservation: Reservation) -> dict:
    """将预约及其关联对象转换成前端直接可展示的数据。"""
    return {
        "id": reservation.id,
        "user_id": reservation.user_id,
        "user_name": reservation.user.full_name or reservation.user.username,
        "lab_id": reservation.lab_id,
        "lab_name": reservation.lab.name,
        "reservation_date": reservation.reservation_date,
        "start_time": reservation.start_time,
        "end_time": reservation.end_time,
        "purpose": reservation.purpose,
        "status": reservation.status,
        "review_comment": reservation.review_comment,
        "create_time": reservation.create_time,
    }


def reservation_query(db: Session):
    """所有预约查询统一预加载用户与实验室，防止列表出现 N+1 查询。"""
    return db.query(Reservation).options(
        joinedload(Reservation.user), joinedload(Reservation.lab)
    )


@router.post("")
def create_reservation(
    data: ReservationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生提交预约，初始状态为待审核。"""
    reservation = create_reservation_record(db, current_user.id, data)
    # 重新读取一次以加载 user 和 lab 关联信息。
    reservation = reservation_query(db).filter(Reservation.id == reservation.id).first()
    return Response.success(message="预约申请已提交", data=reservation_to_dict(reservation))


@router.get("/mine")
def get_my_reservations(
    status: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = reservation_query(db).filter(Reservation.user_id == current_user.id)
    if status:
        query = query.filter(Reservation.status == status)
    items = query.order_by(Reservation.id.desc()).all()
    return Response.success(data=[reservation_to_dict(item) for item in items])


@router.put("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 与管理员审核锁定同一条预约行，避免双方同时读取 pending 后互相覆盖结果。
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


@router.get("")
def get_reservation_list(
    status: str = "",
    lab_id: int | None = None,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员查看全部预约，并可按状态和实验室筛选。"""
    query = reservation_query(db)
    if status:
        query = query.filter(Reservation.status == status)
    if lab_id:
        query = query.filter(Reservation.lab_id == lab_id)
    items = query.order_by(Reservation.id.desc()).all()
    return Response.success(data=[reservation_to_dict(item) for item in items])


@router.put("/{reservation_id}/review")
def review_reservation(
    reservation_id: int,
    data: ReservationReview,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员审核预约，只允许通过或拒绝。"""
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
        # 从提交到审核期间，日期可能已经过去，实验室也可能被管理员暂停开放。
        # 审核前复核一次，避免批准已经无法履行的预约。
        now = datetime.now()
        if reservation.reservation_date < now.date() or (
            reservation.reservation_date == now.date()
            and reservation.start_time <= now.time()
        ):
            raise BusinessException(code=BizCode.BAD_REQUEST, message="预约时间已经过去，不能通过审核")
        lab = db.query(Lab).filter(Lab.id == reservation.lab_id).with_for_update().first()
        if not lab or lab.status != 1:
            raise BusinessException(code=BizCode.BAD_REQUEST, message="实验室当前未开放，不能通过审核")

    reservation.status = data.status
    reservation.review_comment = data.review_comment
    db.commit()
    return Response.success(message="预约审核完成")
```

[`fronted/src/api/reservation.js`](../../fronted/src/api/reservation.js)（当前完整内容；被第 18、19 节共用）：

```js
import request from '@/utils/request'

export function createReservationApi(data) {
  return request.post('/api/reservations', data)
}

export function getMyReservationListApi(params) {
  return request.get('/api/reservations/mine', { params })
}

export function cancelReservationApi(reservationId) {
  return request.put(`/api/reservations/${reservationId}/cancel`)
}

export function getReservationListApi(params) {
  return request.get('/api/reservations', { params })
}

export function reviewReservationApi(reservationId, data) {
  return request.put(`/api/reservations/${reservationId}/review`, data)
}
```

**冲突公式推演：** 两个半开区间 `[s1,e1)` 与 `[s2,e2)` 相交 ⇔ `s1 < e2` 且 `s2 < e1`。所以“前一单结束恰好等于下一单开始”（`e1 == s2`）不冲突，可以相邻；完全重叠和部分重叠都满足公式，均被判冲突。`pending` 与 `approved` 都占用时段。

**验证：** 提交完全重叠、部分重叠、相邻三种情况，前两种报 400、最后一种成功。MySQL 下创建预约还会 `with_for_update()` 锁实验室行处理并发；SQLite 测试忽略该锁。注意当前前端只给学生显示预约按钮，但后端创建接口允许**任意已登录用户**调用。

## 第 19 节：我的预约与预约审核

**知识点清单：** 状态机 `pending/approved/rejected/cancelled`、学生只看自己、管理员看全部、取消与审核锁同一预约行、审核前复核状态与时间、`joinedload` 预加载、前端表格按状态渲染不同按钮。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 状态与列表/审核接口 | [`backend/app/api/reservation.py`](../../backend/app/api/reservation.py) | `get_my_reservations`、`get_reservation_list`、`cancel_reservation`、`review_reservation`（第 18 节已贴完整） |
| 前端接口 | [`fronted/src/api/reservation.js`](../../fronted/src/api/reservation.js) | 五个 API 函数（第 18 节已贴完整） |
| 预约页面 | [`fronted/src/views/reservation.vue`](../../fronted/src/views/reservation.vue) | 完整组件（见下） |

[`fronted/src/views/reservation.vue`](../../fronted/src/views/reservation.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 只有一行“已处理”灰字，省略）：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '预约审核' : '我的预约' }}</h1>
      <el-button v-if="!isAdmin" type="primary" @click="$router.push('/lab')">发起预约</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="statusValue" clearable placeholder="全部状态" style="width: 160px" @change="loadReservationList">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-if="isAdmin" v-model="selectedLabId" clearable placeholder="全部实验室" style="width: 190px" @change="loadReservationList">
        <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-button @click="loadReservationList">刷新</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="reservationList" stripe>
      <el-table-column v-if="isAdmin" prop="user_name" label="预约人" min-width="110" />
      <el-table-column prop="lab_name" label="实验室" min-width="140" />
      <el-table-column prop="reservation_date" label="预约日期" width="120" />
      <el-table-column label="预约时间" width="150">
        <template #default="scope">{{ formatTime(scope.row.start_time) }} - {{ formatTime(scope.row.end_time) }}</template>
      </el-table-column>
      <el-table-column prop="purpose" label="用途" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="statusMap[scope.row.status]?.type">{{ statusMap[scope.row.status]?.label || scope.row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="review_comment" label="审核意见" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="scope">
          <template v-if="isAdmin && scope.row.status === 'pending'">
            <el-button link type="success" @click="openReviewDialog(scope.row, 'approved')">通过</el-button>
            <el-button link type="danger" @click="openReviewDialog(scope.row, 'rejected')">拒绝</el-button>
          </template>
          <el-button v-else-if="!isAdmin && ['pending', 'approved'].includes(scope.row.status)" link type="danger" @click="cancelReservation(scope.row)">取消预约</el-button>
          <span v-else class="operation-finished">已处理</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="reviewDialogVisible" :title="reviewForm.status === 'approved' ? '通过预约' : '拒绝预约'" width="460px">
      <el-form label-position="top">
        <el-form-item label="审核意见">
          <el-input v-model="reviewForm.review_comment" type="textarea" :rows="4" :placeholder="reviewForm.status === 'rejected' ? '建议填写拒绝原因' : '可填写使用注意事项'" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="reviewDialogVisible = false">取消</el-button><el-button :type="reviewForm.status === 'approved' ? 'success' : 'danger'" :loading="savingValue" @click="saveReview">确认</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLabListApi } from '@/api/lab'
import { cancelReservationApi, getMyReservationListApi, getReservationListApi, reviewReservationApi } from '@/api/reservation'
import { useUser } from '@/utils/user'

const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const statusValue = ref('')
const selectedLabId = ref(null)
const labList = ref([])
const reservationList = ref([])
const reviewDialogVisible = ref(false)
const selectedReservation = ref(null)
const reviewForm = reactive({ status: 'approved', review_comment: '' })

const statusOptions = [
  { label: '待审核', value: 'pending' }, { label: '已通过', value: 'approved' },
  { label: '已拒绝', value: 'rejected' }, { label: '已取消', value: 'cancelled' }
]
const statusMap = {
  pending: { label: '待审核', type: 'warning' }, approved: { label: '已通过', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' }, cancelled: { label: '已取消', type: 'info' }
}

const loadReservationList = async () => {
  loadingValue.value = true
  try {
    const params = { status: statusValue.value, lab_id: selectedLabId.value || undefined }
    const res = isAdmin.value ? await getReservationListApi(params) : await getMyReservationListApi(params)
    reservationList.value = res.data
  } finally { loadingValue.value = false }
}

const formatTime = (value) => value?.slice(0, 5) || '--:--'
const openReviewDialog = (reservation, status) => {
  selectedReservation.value = reservation
  Object.assign(reviewForm, { status, review_comment: '' })
  reviewDialogVisible.value = true
}

const saveReview = async () => {
  savingValue.value = true
  try {
    await reviewReservationApi(selectedReservation.value.id, reviewForm)
    ElMessage.success('预约审核完成')
    reviewDialogVisible.value = false
    await loadReservationList()
  } finally { savingValue.value = false }
}

const cancelReservation = async (reservation) => {
  try {
    await ElMessageBox.confirm('确定取消这条预约吗？', '取消确认', { type: 'warning' })
  } catch {
    // 关闭确认框表示保留预约，直接返回，避免产生未处理的 Promise 拒绝。
    return
  }
  await cancelReservationApi(reservation.id)
  ElMessage.success('预约已取消')
  await loadReservationList()
}

onMounted(async () => {
  if (isAdmin.value) {
    const res = await getLabListApi()
    labList.value = res.data
  }
  await loadReservationList()
})
</script>
```

**数据流：** 学生进入页面 → `getMyReservationListApi` 只返回 `user_id == current_user.id` 的记录；管理员走 `getReservationListApi` 看全部。审核时后端先 `with_for_update()` 锁行，再检查 `status == "pending"`，“通过”还要复核时间未过、实验室仍开放。状态变化后前端旧按钮隐藏只是体验，后端每次仍重新校验。

**验证：** 走“学生提交 → 管理员通过 → 学生查看”；再测拒绝、取消、重复审核（第二次应报 400 “该预约已经处理”）。

## 本组自检

- 能画出预约的 `pending → approved/rejected` 与可取消状态，并用半开区间公式证明时间冲突判断。
- 能说明为什么普通接口与 AI 工具必须调用同一个 `create_reservation_record`。
- 能解释 `joinedload` 解决了什么、`with_for_update()` 在 MySQL 与 SQLite 的差别。
- 能指出 `only_open`、`only_available` 是查询选项而非强制数据权限。


---

# 第四部分：AI 助手、RAG、Tool Calling、LangGraph 与 SSE

## 第 20 节：开发实验室 AI 助手对话（后端部分）

**知识点清单：** `Literal` 限定历史角色、`Field` 长度与数量上限、`default_factory=list` 避免共享可变默认值、`StreamingResponse(media_type="text/event-stream")`、SSE 帧格式 `event:`/`data:` + 空行结尾、流式生成器里**自己开数据库会话并在 `finally` 关闭**、`tool_start`/`tool_end` 过程事件转发、`Cache-Control: no-cache` 与 `X-Accel-Buffering: no`。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 请求体校验 | [`backend/app/schemas/ai.py`](../../backend/app/schemas/ai.py) | `ChatMessage`、`ChatRequest` |
| SSE 帧拼装 | [`backend/app/api/ai.py`](../../backend/app/api/ai.py) | `sse_event` |
| 流式响应与会话生命周期 | [`backend/app/api/ai.py`](../../backend/app/api/ai.py) | `chat_stream`、`generate_events` |
| 路由挂载 | [`backend/app/api/__init__.py`](../../backend/app/api/__init__.py) | `api_router.include_router(ai.router)`（第 04 节已贴完整） |

**完整源码：**

[`backend/app/schemas/ai.py`](../../backend/app/schemas/ai.py)（当前完整内容）：

```python
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    # 历史消息只接受用户和助手角色，避免客户端伪造 system/developer 指令。
    role: Literal["user", "assistant"]
    # 单条历史消息限长，防止请求体过大以及无意中消耗过多模型上下文。
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    # 当前问题允许容纳完整预约描述，但仍设置合理上限。
    message: str = Field(min_length=1, max_length=2000)
    # 仅保留少量历史消息，防止一次请求携带无限上下文。
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
```

[`backend/app/api/ai.py`](../../backend/app/api/ai.py)（当前完整内容）：

```python
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.ai.agent import GRAPH_ENGINE, build_prompt_context, run_graph, run_model_tools, stream_answer
from app.database import SessionLocal
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatRequest

router = APIRouter(prefix="/ai", tags=["AI 实验室助手"])
logger = logging.getLogger("lab_agent.ai")


def sse_event(event: str, data: dict) -> str:
    """SSE 每条消息以空行结束，data 使用 JSON 便于前端稳定解析。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
def chat_stream(data: ChatRequest, current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    history = [item.model_dump() for item in data.history]

    def generate_events():
        db = SessionLocal()
        try:
            yield sse_event("status", {"message": f"正在通过 {GRAPH_ENGINE} 分析问题…"})
            state = run_graph(data.message, user_id, db, history)
            yield sse_event("status", {"message": f"已使用 {state.get('retrieval_engine', '知识库')} 完成 RAG 检索"})

            # 模型工具调用：逐个发 tool_start/tool_end 事件
            model_tool_results = []
            for event in run_model_tools(data.message, user_id, db, history):
                if event["type"] == "tool_start":
                    yield sse_event("tool_start", {"label": event["label"]})
                elif event["type"] == "tool_end":
                    yield sse_event("tool_end", {"label": event["label"]})
                elif event["type"] == "done":
                    model_tool_results = event["results"]

            used_tools = state.get("used_tools", [])
            if model_tool_results:
                used_tools.append("AI Tool Calling")
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

    return StreamingResponse(generate_events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

**为什么 `db` 在生成器里创建：** 不能写成 `db: Session = Depends(get_db)`。`Depends(get_db)` 的 `finally` 会在**接口函数返回时**触发，而此时响应体还没开始迭代，会话已经被关掉了。所以在生成器内部 `SessionLocal()` 自己开、`finally` 自己关。

**验证：** 用 `curl -N` 调用（`-N` 关闭缓冲）看到逐条 `event:`/`data:`；不带 Token 返回 401；`message` 传空串返回 422。

## 第 21 节：开发实验室 AI 助手对话（前端与联调）

**知识点清单：** SSE POST 必须用 `fetch` 而非 axios（axios 浏览器端不能逐块读响应体）、`response.body.getReader()` + `TextDecoder(stream: true)`、按 `/\r?\n\r?\n/` 切事件块并保留最后一段残缺 buffer、`AbortController` 取消、**Pinia store 承接对话状态与请求**（切换页面不丢消息、回答在后台继续生成）、`history` 必须在插入本轮空白回复**之前**生成。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| fetch 流式读取与 SSE 解析 | [`fronted/src/api/ai.js`](../../fronted/src/api/ai.js) | `streamChatApi`、`handleEventBlock` |
| 401 单独处理 | [`fronted/src/api/ai.js`](../../fronted/src/api/ai.js) | `if (response.status === 401)` |
| 对话状态与流程 | [`fronted/src/store/chat.js`](../../fronted/src/store/chat.js) | `useChatStore`：`sendMessage`、`stop`、`clearMessages` |
| 发送与中止 | [`fronted/src/views/chat.vue`](../../fronted/src/views/chat.vue) | `sendMessage`、`stopAnswer`（转调 store） |
| 页面结构 | [`fronted/src/views/chat.vue`](../../fronted/src/views/chat.vue) | 完整组件（见下） |

**完整源码：**

[`fronted/src/api/ai.js`](../../fronted/src/api/ai.js)（当前完整内容）：

```js
import router from '@/router'
import { getToken, logout } from '@/utils/auth'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export async function streamChatApi(data, onEvent, signal) {
  // 浏览器中的 axios 不能像 fetch 一样逐块读取响应体，因此 SSE POST 使用 fetch。
  const response = await fetch(`${apiBaseUrl}/api/ai/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`
    },
    body: JSON.stringify(data),
    signal
  })

  // SSE 使用 fetch，不会走 axios 响应拦截器，因此 401 需要在这里单独处理。
  if (response.status === 401) {
    const redirectPath = router.currentRoute.value.fullPath
    logout()
    await router.replace({ path: '/login', query: { redirect: redirectPath } })
    throw new Error('登录已失效，请重新登录')
  }

  if (!response.ok || !response.body) {
    throw new Error('AI 服务请求失败')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  // 把一个 SSE 事件块解析成“事件名 + JSON 数据”。
  // 后端当前每个事件只有一行 data，所以可以直接解析。
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
    // 同时兼容 LF 和 CRLF 换行。最后一段可能还没有收到空行，先留在 buffer。
    const eventBlocks = buffer.split(/\r?\n\r?\n/)
    buffer = eventBlocks.pop() || ''

    for (const block of eventBlocks) {
      handleEventBlock(block)
    }
    if (done) {
      // 网关或代理有时会在最后一条事件后直接断开，不再补一个空行。
      // 此时也要消费剩余 buffer，避免丢掉最后一个 token 或 done 事件。
      handleEventBlock(buffer)
      break
    }
  }
}
```

[`fronted/src/views/chat.vue`](../../fronted/src/views/chat.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 纯 CSS 省略）：

```vue
<template>
  <div class="chat-page">
    <header class="chat-header">
      <div>
        <h1>AI 实验室助手</h1>
        <p>支持知识库问答、实验室/设备查询和智能预约</p>
      </div>
      <el-tag type="success" effect="plain">SSE 流式输出</el-tag>
    </header>

    <main ref="messageContainer" class="message-container">
      <div v-for="(message, index) in chatStore.messages" :key="index" :class="['message-row', message.role]">
        <el-avatar :size="36">{{ message.role === 'user' ? '我' : 'AI' }}</el-avatar>
        <div class="message-content">
          <div class="message-bubble">{{ message.content || '正在思考…' }}</div>
          <div v-if="message.events?.length" class="process-events">
            <el-tag v-for="event in message.events" :key="event" size="small" effect="plain">{{ event }}</el-tag>
          </div>
        </div>
      </div>
    </main>

    <div class="suggestions">
      <button v-for="question in suggestions" :key="question" type="button" @click="inputValue = question">{{ question }}</button>
    </div>

    <footer class="chat-input">
      <el-input v-model="inputValue" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" resize="none" placeholder="输入问题；Enter 发送，Shift+Enter 换行" :disabled="chatStore.sending" @keydown.enter.exact.prevent="sendMessage" />
      <el-button v-if="chatStore.sending" type="danger" plain @click="stopAnswer">停止</el-button>
      <el-button v-else type="primary" :disabled="!inputValue.trim()" @click="sendMessage">发送</el-button>
    </footer>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { useChatStore } from '@/store/chat'

const inputValue = ref('')
const messageContainer = ref(null)
const chatStore = useChatStore()

const suggestions = [
  '当前有哪些开放的实验室和设备？',
  '实验室预约需要遵守哪些规则？',
  '设备发生故障时应该怎么处理？'
]

const scrollToBottom = async () => {
  await nextTick()
  if (messageContainer.value) messageContainer.value.scrollTop = messageContainer.value.scrollHeight
}

// 对话逻辑在 store 里，组件只负责渲染。
// 深度监听 messages 变化（包括同一条消息 content 逐 token 增长），自动滚动到底部。
watch(() => chatStore.messages, scrollToBottom, { deep: true })

const sendMessage = () => {
  const question = inputValue.value.trim()
  if (!question || chatStore.sending) return
  inputValue.value = ''
  chatStore.sendMessage(question)
}

const stopAnswer = () => {
  chatStore.stop()
}
</script>
```

[`fronted/src/store/chat.js`](../../fronted/src/store/chat.js)（当前完整内容；对话状态与 SSE 流程都放在 Pinia store 里，切换页面消息不丢失）：

```js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamChatApi } from '@/api/ai'

/**
 * 对话全局状态 + 对话流程。
 * 把消息和 SSE 请求都放在 Pinia store 里，
 * 用户跳到其他页面时组件销毁但 store 不销毁，
 * AI 回答会在后台继续生成，回来时能看到完整内容。
 */
export const useChatStore = defineStore('chat', () => {
  const welcomeMessage = {
    role: 'assistant',
    content: '你好，我是实验室 AI 助手。你可以向我查询实验室、设备、预约规则，也可以让我协助创建预约。',
    events: []
  }

  const messages = ref([{ ...welcomeMessage }])
  const sending = ref(false)
  let abortController = null

  function addMessage(message) {
    messages.value.push(message)
  }

  function clearMessages() {
    messages.value = [{ ...welcomeMessage }]
  }

  async function sendMessage(question) {
    if (!question || sending.value) return

    // 历史消息必须在加入本轮空白回复之前生成。
    const history = messages.value.slice(-10).map(({ role, content }) => ({ role, content }))
    addMessage({ role: 'user', content: question, events: [] })

    // 用普通对象即可，store 的 messages 本身是响应式的，
    // 修改对象属性会触发视图更新。
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
        // 在还没有 token 时停止，不要让空白气泡一直显示"正在思考"。
        if (!assistantMessage.content) assistantMessage.content = '已停止生成。'
        assistantMessage.events.push('用户已停止回答')
      } else {
        assistantMessage.content = assistantMessage.content || 'AI 助手暂时无法回答，请稍后重试。'
      }
    } finally {
      // 只允许当前请求清理自己的状态，避免旧请求误清理新请求的控制器。
      if (abortController === currentController) {
        sending.value = false
        abortController = null
      }
    }
  }

  function stop() {
    // 这里只发出取消信号，sending 由请求的 finally 统一收尾。
    abortController?.abort()
  }

  return { messages, sending, sendMessage, stop, addMessage, clearMessages }
})
```

**三个易错点：**

1. `history` 必须在 `push` 空白助手消息**之前**算好，否则本轮的空内容会被当成历史发回后端。
2. 对话状态放在 Pinia store：组件销毁了 store 还在，回答会在后台继续生成；`messages` 本身是响应式的，回复对象用普通对象即可，不必再手动 `reactive()`。
3. `sending` 只在 `finally` 里由**当前**请求复位，`stop()` 只调 `abort()`。否则用户连点会串状态，或者旧请求误清新请求的状态。

**验证：** 输入“实验室预约需要遵守哪些规则？”看到逐字输出与 `status`/`tool_start`/`tool_end`/`tool` 过程标签；点“停止”后气泡显示“已停止生成。”；切到其他页面再回来，对话和后台生成不丢失；删掉 `localStorage` 里的 Token 再发问，应跳回登录页并带 `redirect`。

## 第 22 节：用 RAG 给实验室助手接入知识库

**知识点清单：** Markdown 目录作为知识源、`glob("*.md")` + `sorted` 保证顺序可复现、**按段落分块**（按空行分段，累积到 200 字以上切一块，块 ID 形如 `safety_chunk0`）、**确定性本地嵌入** `build_local_embedding`（blake2b 哈希 + 正负号 + L2 归一化）、`build_content_hash` 用内容指纹而非文件时间判断是否改动、`sync_collection` 的增/改/删增量同步、`upsert(embeddings=...)` 显式传向量以避免联网下载模型、空 collection 直接返回、异常降级到 `simple_search`。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 知识源加载 | [`backend/app/ai/knowledge.py`](../../backend/app/ai/knowledge.py) | `KNOWLEDGE_DIR`、`load_documents` |
| 离线向量 | [`backend/app/ai/knowledge.py`](../../backend/app/ai/knowledge.py) | `build_local_embedding` |
| 增量同步 | [`backend/app/ai/knowledge.py`](../../backend/app/ai/knowledge.py) | `build_content_hash`、`sync_collection` |
| 检索与降级 | [`backend/app/ai/knowledge.py`](../../backend/app/ai/knowledge.py) | `search_documents`、`simple_search` |
| 知识内容本身 | [`backend/app/knowledge/lab_rules.md`](../../backend/app/knowledge/lab_rules.md)、[`equipment_guide.md`](../../backend/app/knowledge/equipment_guide.md) | 见下 |
| 回归测试 | [`backend/tests/test_knowledge.py`](../../backend/tests/test_knowledge.py) | `KnowledgeIndexSyncTest` |

**完整源码：**

[`backend/app/ai/knowledge.py`](../../backend/app/ai/knowledge.py)（当前完整内容）：

```python
import hashlib
import logging
import math
from pathlib import Path


KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "chroma_db"
logger = logging.getLogger(__name__)


def load_documents() -> list[dict[str, str]]:
    """读取本地 Markdown 知识，按段落分块，每块 200-400 字。"""
    raw_docs = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        raw_docs.append({"id": path.stem, "source": path.name, "text": path.read_text("utf-8")})

    # 分块：按空行分段，累积到 200 字以上就切一块
    chunks = []
    for doc in raw_docs:
        paragraphs = [p.strip() for p in doc["text"].split("\n\n") if p.strip()]
        current = ""
        for i, para in enumerate(paragraphs):
            current += para + "\n\n"
            if len(current) >= 200 or i == len(paragraphs) - 1:
                chunks.append({
                    "id": f"{doc['id']}_chunk{len([c for c in chunks if c['id'].startswith(doc['id'])])}",
                    "source": doc["source"],
                    "text": current.strip(),
                })
                current = ""
    return chunks


def simple_search(query: str, limit: int = 3) -> list[dict[str, str]]:
    """无 ChromaDB 时使用字符命中数排序，保证项目仍可独立运行。"""
    keywords = {char for char in query.lower() if char.strip()}
    scored = []
    for document in load_documents():
        score = sum(document["text"].lower().count(keyword) for keyword in keywords)
        scored.append((score, document))
    return [item[1] for item in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def build_local_embedding(text: str, dimensions: int = 128) -> list[float]:
    """把文本转换成可复现的轻量向量，避免首次运行再下载额外模型。

    ChromaDB 默认会下载一个英文嵌入模型。课程项目在网络较慢、没有模型缓存时，
    第一次检索可能长时间卡住。这里使用“字符 + 相邻双字符”的哈希向量：它不依赖
    网络，适合本项目规模较小的中文知识库。以后接入正式嵌入模型时，只需替换这个
    函数，下面的 ChromaDB 存储和查询逻辑都不需要修改。
    """
    normalized_text = "".join(text.lower().split())
    if not normalized_text:
        return [0.0] * dimensions

    # 单字符能覆盖关键词；相邻双字符能保留一部分中文词语信息。
    tokens = list(normalized_text)
    tokens.extend(normalized_text[index : index + 2] for index in range(len(normalized_text) - 1))

    vector = [0.0] * dimensions
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        vector_index = int.from_bytes(digest[:2], "big") % dimensions
        direction = 1.0 if digest[2] % 2 else -1.0
        vector[vector_index] += direction

    # L2 归一化后，ChromaDB 的距离比较不会被文档长度主导。
    vector_length = math.sqrt(sum(value * value for value in vector))
    return [value / vector_length for value in vector] if vector_length else vector


def build_content_hash(text: str) -> str:
    """计算文档内容指纹，用来判断 Markdown 是否真正发生了修改。

    不直接使用文件修改时间，因为复制、解压等操作会改变时间却不改变内容，
    SHA-256 可以避免这类无意义的重复向量化。
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sync_collection(collection, documents: list[dict[str, str]]) -> None:
    """把本地 Markdown 的新增、修改和删除同步到 ChromaDB。

    同步规则：
    1. 本地新增文件：通过 ``upsert`` 写入；
    2. 内容指纹或文件名变化：重新计算向量并更新；
    3. 本地已删除文件：从 collection 中删除对应记录。

    每次 upsert 都显式传入 ``embeddings``，因此 ChromaDB 不会调用默认
    嵌入函数，也不会在首次运行时联网下载模型。
    """
    indexed = collection.get(include=["metadatas"])
    indexed_ids = indexed.get("ids") or []
    indexed_metadatas = indexed.get("metadatas") or []

    # 旧版索引可能没有 content_hash，此时会被视为需要更新，
    # 从而自动完成索引格式迁移，不需要手动删除 chroma_db。
    indexed_metadata_by_id = {
        document_id: (metadata or {})
        for document_id, metadata in zip(indexed_ids, indexed_metadatas)
    }
    local_document_by_id = {document["id"]: document for document in documents}

    deleted_ids = sorted(set(indexed_ids) - set(local_document_by_id))
    if deleted_ids:
        collection.delete(ids=deleted_ids)

    changed_documents = []
    for document in documents:
        old_metadata = indexed_metadata_by_id.get(document["id"], {})
        current_hash = build_content_hash(document["text"])
        if (
            old_metadata.get("content_hash") != current_hash
            or old_metadata.get("source") != document["source"]
        ):
            changed_documents.append((document, current_hash))

    if changed_documents:
        collection.upsert(
            ids=[document["id"] for document, _ in changed_documents],
            documents=[document["text"] for document, _ in changed_documents],
            metadatas=[
                {"source": document["source"], "content_hash": content_hash}
                for document, content_hash in changed_documents
            ],
            # 使用项目内的确定性向量，保证离线可运行。
            embeddings=[build_local_embedding(document["text"]) for document, _ in changed_documents],
        )


def search_documents(query: str, limit: int = 3) -> tuple[list[dict[str, str]], str]:
    """优先使用 ChromaDB 向量检索，依赖不可用时自动切换到本地检索。"""
    try:
        import chromadb

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_or_create_collection(name="lab_knowledge")
        documents = load_documents()
        # 检索前做一次轻量增量同步，课程知识库修改后无需重启服务。
        sync_collection(collection, documents)

        # 空知识库时直接返回，避免对空 collection 执行 n_results=1。
        document_count = collection.count()
        if document_count == 0 or limit <= 0:
            return [], "ChromaDB"

        result = collection.query(
            query_embeddings=[build_local_embedding(query)],
            n_results=min(limit, document_count),
        )
        items = []
        for text, metadata in zip(result.get("documents", [[]])[0], result.get("metadatas", [[]])[0]):
            items.append({"text": text, "source": metadata.get("source", "knowledge")})
        return items, "ChromaDB"
    except Exception as exc:
        # RAG 不是登录、预约等核心业务的硬依赖：向日志记录真实原因，再安全降级，
        # 这样用户仍能使用 AI 页面，开发者也能从后端终端快速定位依赖问题。
        logger.warning("ChromaDB 检索失败，已切换到本地关键词检索：%s", exc)
        return simple_search(query, limit), "本地关键词检索"
```

[`backend/app/knowledge/lab_rules.md`](../../backend/app/knowledge/lab_rules.md)（当前完整内容）——它同时是**业务规则的文字版**，与 [`services/reservation.py`](../../backend/app/services/reservation.py) 的代码校验一一对应：

```markdown
# 实验室预约规则

1. 用户只能预约状态为“开放”的实验室。
2. 预约日期不能早于当天，结束时间必须晚于开始时间。
3. 同一实验室的待审核或已通过预约不能出现时间重叠。
4. 新预约默认为待审核，管理员通过后方可按预约时间使用。
5. 用户可以取消待审核或已通过的预约；已拒绝、已取消的预约不能再次取消。
6. 进入实验室后应遵守安全规范，离开前关闭仪器电源并整理实验台。
```

[`backend/app/knowledge/equipment_guide.md`](../../backend/app/knowledge/equipment_guide.md)（当前完整内容）：

```markdown
# 设备使用与故障处理

使用设备前应先查看设备状态与所属实验室。标记为维护中的设备不可使用。
发现设备故障时不要自行拆卸，应停止操作、保留现场并联系实验室管理员。
预约实验室不代表自动获得所有精密设备的操作资格，特殊设备仍需接受培训。
```

[`backend/tests/test_knowledge.py`](../../backend/tests/test_knowledge.py)（当前完整内容）：

```python
"""RAG 知识库索引同步测试。

测试使用系统临时目录，不读写 ``backend/chroma_db``，也不会修改
项目自带的 Markdown 知识文件。
"""

import gc
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import chromadb
from chromadb.api.client import SharedSystemClient

from app.ai import knowledge


class KnowledgeIndexSyncTest(unittest.TestCase):
    def setUp(self):
        # 每个测试拥有独立的 Markdown 目录和 ChromaDB 目录。
        self.temp_directory = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temp_directory.name)
        self.knowledge_directory = self.temp_root / "knowledge"
        self.chroma_directory = self.temp_root / "chroma_db"
        self.knowledge_directory.mkdir()

        self.knowledge_patch = patch.object(knowledge, "KNOWLEDGE_DIR", self.knowledge_directory)
        self.chroma_patch = patch.object(knowledge, "CHROMA_DIR", self.chroma_directory)
        self.knowledge_patch.start()
        self.chroma_patch.start()

    def tearDown(self):
        self.chroma_patch.stop()
        self.knowledge_patch.stop()

        # ChromaDB 会缓存已打开的 System；清理缓存后再删临时目录，
        # 避免 Windows 下 SQLite 文件句柄导致临时目录无法回收。
        SharedSystemClient.clear_system_cache()
        gc.collect()
        self.temp_directory.cleanup()

    def write_document(self, filename: str, text: str) -> Path:
        path = self.knowledge_directory / filename
        path.write_text(text, encoding="utf-8")
        return path

    def collection_snapshot(self) -> dict[str, dict]:
        """读取临时 collection，转成以文档 ID 为键的快照方便断言。"""
        client = chromadb.PersistentClient(path=str(self.chroma_directory))
        collection = client.get_collection(name="lab_knowledge")
        result = collection.get(include=["documents", "metadatas"])
        return {
            document_id: {"text": text, "metadata": metadata}
            for document_id, text, metadata in zip(
                result["ids"], result["documents"], result["metadatas"]
            )
        }

    def test_markdown_add_update_and_delete_are_synchronized(self):
        """新增、修改、删除 Markdown 后，索引应在下次检索前同步。"""
        safety_path = self.write_document("safety.md", "实验安全：进入实验室前需要登记。")

        _, backend = knowledge.search_documents("实验安全")
        self.assertEqual(backend, "ChromaDB")
        snapshot = self.collection_snapshot()
        # 知识库按段落分块后写入，短文档只有一个 chunk0。
        self.assertEqual(set(snapshot), {"safety_chunk0"})
        old_hash = snapshot["safety_chunk0"]["metadata"]["content_hash"]

        # 修改已有文件：ID 不变，但文本和内容指纹都应被 upsert。
        safety_path.write_text("实验安全：进入前登记，离开时关闭电源。", encoding="utf-8")
        knowledge.search_documents("关闭电源")
        snapshot = self.collection_snapshot()
        self.assertIn("关闭电源", snapshot["safety_chunk0"]["text"])
        self.assertNotEqual(old_hash, snapshot["safety_chunk0"]["metadata"]["content_hash"])

        # 新增文件：无需清空索引，下次检索会增量写入。
        self.write_document("equipment.md", "设备管理：显微镜使用后需要归还。")
        knowledge.search_documents("显微镜")
        self.assertEqual(set(self.collection_snapshot()), {"safety_chunk0", "equipment_chunk0"})

        # 删除本地文件：对应向量不应残留在 ChromaDB 中。
        safety_path.unlink()
        results, backend = knowledge.search_documents("实验安全")
        snapshot = self.collection_snapshot()
        self.assertEqual(backend, "ChromaDB")
        self.assertEqual(set(snapshot), {"equipment_chunk0"})
        self.assertTrue(all(item["source"] != "safety.md" for item in results))

    def test_chromadb_error_falls_back_to_keyword_search(self):
        """ChromaDB 无法创建时，仍应返回本地关键词检索结果。"""
        self.write_document("rules.md", "预约规则：请提前一天申请实验室。")
        invalid_chroma_path = self.temp_root / "not-a-directory"
        invalid_chroma_path.write_text("这是文件，不是目录", encoding="utf-8")

        with patch.object(knowledge, "CHROMA_DIR", invalid_chroma_path):
            results, backend = knowledge.search_documents("预约实验室")

        self.assertEqual(backend, "本地关键词检索")
        self.assertEqual(results[0]["source"], "rules.md")


if __name__ == "__main__":
    unittest.main()
```

**向量怎么来的（128 维）：** 文本去掉所有空白并转小写 → 拆成单字符 token + 相邻双字符 token → 每个 token 用 `blake2b(digest_size=4)` 取 4 字节 → 前 2 字节 `% 128` 决定落在哪一维，第 3 字节奇偶决定 `+1`/`-1` → 最后整体 L2 归一化。同一段文本永远得到同一个向量，所以 `test_local_embedding_is_stable` 能断言两次结果相等。

**为什么要内容指纹：** 复制、解压会改文件时间却不改内容；只看 mtime 会反复重复向量化。SHA-256 只在内容真变时才 upsert。旧索引没有 `content_hash` 字段时会被判为“需要更新”，于是**自动完成索引迁移**，不必手动删 `chroma_db`。

**验证：** 跑 `python -m unittest tests.test_knowledge`；再改一句 `lab_rules.md` 不重启服务直接问 AI，回答应反映新内容；把 `chroma_db` 目录做成一个同名文件，提问仍能回答（降级为“本地关键词检索”）。

## 第 23 节：用 Tool Calling 让助手查询实验室数据

**知识点清单：** `TOOL_SCHEMAS` 用 Chat Completions 的 `{"type": "function", "function": {...}}` 包装、`strict: True` + `additionalProperties: False`、读工具 `list_open_labs` 直接查库、写工具 `create_lab_reservation` **重新做完整校验且不信任模型参数**、写工具复用 `create_reservation_record`、从 `response.choices[0].message.tool_calls` 取 `function.name` 与 `function.arguments`（JSON 字符串要 `json.loads`）、统一由 `_execute_tool` 分发、`tool_start`/`tool_end` 向前端暴露执行过程、每轮最多执行一次写工具。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 工具声明 | [`backend/app/ai/tools.py`](../../backend/app/ai/tools.py) | `TOOL_SCHEMAS` |
| 读工具 | [`backend/app/ai/tools.py`](../../backend/app/ai/tools.py) | `list_open_labs` |
| 写工具 | [`backend/app/ai/tools.py`](../../backend/app/ai/tools.py) | `create_lab_reservation` |
| 模型侧调度 | [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) | `run_model_tools`（附录完整） |
| 落库规则 | [`backend/app/services/reservation.py`](../../backend/app/services/reservation.py) | `create_reservation_record`（第 18 节已贴完整） |

**完整源码：**

[`backend/app/ai/tools.py`](../../backend/app/ai/tools.py)（当前完整内容；为便于阅读按原文件顺序排列，内容未增删）：

```python
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.blackout import BlackoutPeriod
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.common.exceptions import BusinessException
from app.schemas.reservation import ReservationCreate
from app.services.reservation import create_reservation_record


TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "list_open_labs", "description": "查询当前开放的实验室以及可用设备", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "search_lab_docs", "description": "查询实验室预约规则、设备使用规范等知识库文档", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "create_lab_reservation", "description": "信息完整并得到用户明确要求后，创建实验室预约", "parameters": {"type": "object", "properties": {"lab_id": {"type": "integer"}, "reservation_date": {"type": "string", "description": "YYYY-MM-DD"}, "start_time": {"type": "string", "description": "HH:MM"}, "end_time": {"type": "string", "description": "HH:MM"}, "purpose": {"type": "string"}}, "required": ["lab_id", "reservation_date", "start_time", "end_time", "purpose"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "get_my_reservations", "description": "查询当前用户的预约记录，可按状态筛选", "parameters": {"type": "object", "properties": {"status": {"type": "string", "enum": ["pending", "approved", "rejected", "cancelled"], "description": "预约状态，留空查全部"}}, "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "cancel_reservation", "description": "取消用户自己的预约，需要提供预约ID", "parameters": {"type": "object", "properties": {"reservation_id": {"type": "integer", "description": "要取消的预约ID"}}, "required": ["reservation_id"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "check_lab_availability", "description": "查询某实验室某天哪些时段已被占用或不可约", "parameters": {"type": "object", "properties": {"lab_id": {"type": "integer"}, "reservation_date": {"type": "string", "description": "YYYY-MM-DD"}}, "required": ["lab_id", "reservation_date"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "get_latest_announcements", "description": "查询系统最新公告", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "recommend_lab", "description": "根据日期、时间段偏好和需要时长，智能推荐有空位的实验室。学生说想什么时候做实验但没指定实验室时用这个工具", "parameters": {"type": "object", "properties": {"reservation_date": {"type": "string", "description": "YYYY-MM-DD"}, "period": {"type": "string", "enum": ["morning", "afternoon", "evening"], "description": "偏好时段：上午=8-12点，下午=13-18点，晚上=18-22点"}, "duration_hours": {"type": "integer", "description": "需要几小时，默认2"}}, "required": ["reservation_date", "period"], "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "get_today", "description": "获取今天的日期和星期几。用户说今天、明天、后天时先用这个换算成具体日期", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, "strict": True},
    {"type": "function", "function": {"name": "list_lab_equipments", "description": "查询所有实验室的设备列表，包括设备名、数量和所属实验室", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, "strict": True},
]


def list_open_labs(db: Session) -> str:
    labs = db.query(Lab).filter(Lab.status == 1).order_by(Lab.id).all()
    if not labs:
        return "当前没有开放的实验室。"
    lines = []
    for lab in labs:
        equipment = db.query(Equipment).filter(Equipment.lab_id == lab.id, Equipment.status == 1, Equipment.quantity > 0).all()
        equipment_text = "、".join(f"{item.name}×{item.quantity}" for item in equipment) or "暂无登记设备"
        lines.append(f"实验室ID {lab.id}：{lab.name}，位置 {lab.location}，容量 {lab.capacity} 人；设备：{equipment_text}")
    return "\n".join(lines)


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


def get_my_reservations(db: Session, user_id: int, status: str | None = None) -> str:
    query = db.query(Reservation).filter(Reservation.user_id == user_id)
    if status:
        query = query.filter(Reservation.status == status)
    items = query.order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc()).limit(20).all()
    if not items:
        return "你当前没有预约记录。"
    status_map = {"pending": "待审核", "approved": "已通过", "rejected": "已拒绝", "cancelled": "已取消"}
    lines = [f"预约共 {len(items)} 条："]
    for r in items:
        lab_name = r.lab.name if r.lab else "未知"
        lines.append(f"#{r.id} {lab_name} {r.reservation_date} {r.start_time.strftime('%H:%M')}-{r.end_time.strftime('%H:%M')} [{status_map.get(r.status, r.status)}] 用途：{r.purpose}")
    return "\n".join(lines)


def cancel_reservation(db: Session, user_id: int, reservation_id: int) -> str:
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        return f"预约 #{reservation_id} 不存在。"
    if reservation.user_id != user_id:
        return f"预约 #{reservation_id} 不是你的，无法取消。"
    if reservation.status not in ("pending", "approved"):
        return f"预约 #{reservation_id} 当前状态为{reservation.status}，不能取消。"
    reservation.status = "cancelled"
    db.commit()
    return f"预约 #{reservation_id} 已取消。"


def check_lab_availability(db: Session, lab_id: int, reservation_date: str) -> str:
    try:
        d = date.fromisoformat(reservation_date)
    except ValueError:
        return "日期格式错误，请用 YYYY-MM-DD。"
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        return f"实验室 #{lab_id} 不存在。"
    items = db.query(Reservation).filter(
        Reservation.lab_id == lab_id,
        Reservation.reservation_date == d,
        Reservation.status.in_(["pending", "approved"]),
    ).order_by(Reservation.start_time).all()
    blackouts = db.query(BlackoutPeriod).filter(
        BlackoutPeriod.lab_id == lab_id,
        BlackoutPeriod.blackout_date == d,
    ).order_by(BlackoutPeriod.start_time).all()
    if not items and not blackouts:
        return f"{lab.name} {reservation_date} 全天空闲，没有已占用或不可约时段。"
    lines = [f"{lab.name} {reservation_date} 不可用时段："]
    for r in items:
        st = "已通过" if r.status == "approved" else "待审核"
        lines.append(f"  {r.start_time.strftime('%H:%M')}-{r.end_time.strftime('%H:%M')}（{r.user.full_name if r.user else '?'}，{st}）")
    for b in blackouts:
        lines.append(f"  {b.start_time.strftime('%H:%M')}-{b.end_time.strftime('%H:%M')}（不可约：{b.reason}）")
    return "\n".join(lines)


def get_latest_announcements(db: Session, limit: int = 5) -> str:
    items = db.query(Announcement).order_by(Announcement.id.desc()).limit(limit).all()
    if not items:
        return "当前没有系统公告。"
    lines = ["最新公告："]
    for a in items:
        lines.append(f"【{a.title}】{a.content[:100]}")
    return "\n".join(lines)


def recommend_lab(db: Session, reservation_date: str, period: str, duration_hours: int = 2) -> str:
    """根据时间段偏好智能推荐有空位的实验室，返回详细选项。

    占用来源既包括已有预约，也包括管理员设置的不可约时段；当天只推荐
    当前时间之后的时段，避免推荐结果在创建时被“开始时间已过”拦住。
    """
    try:
        d = date.fromisoformat(reservation_date)
    except ValueError:
        return "日期格式错误，请用 YYYY-MM-DD。"

    period_map = {
        "morning": (time(8, 0), time(12, 0)),
        "afternoon": (time(13, 0), time(18, 0)),
        "evening": (time(18, 0), time(22, 0)),
    }
    range_start, range_end = period_map.get(period, period_map["afternoon"])
    need_minutes = duration_hours * 60

    now = datetime.now()
    if d < now.date():
        return f"{reservation_date} 已经过去，请选择今天或之后的日期。"
    if d == now.date():
        # 今天把起点抬到下一个 30 分钟刻度，跳过已经过去的时段。
        current_minutes = now.hour * 60 + now.minute
        rounded_minutes = (current_minutes // 30 + 1) * 30
        range_end_minutes = range_end.hour * 60 + range_end.minute
        if rounded_minutes >= range_end_minutes:
            return f"今天 {period} 时段已经过去，建议换个时段或改到明天。"
        range_start = time(hour=rounded_minutes // 60, minute=rounded_minutes % 60)

    labs = db.query(Lab).filter(Lab.status == 1).order_by(Lab.id).all()
    if not labs:
        return "当前没有开放的实验室。"

    results = []
    for lab in labs:
        occupied = db.query(Reservation).filter(
            Reservation.lab_id == lab.id,
            Reservation.reservation_date == d,
            Reservation.status.in_(["pending", "approved"]),
        ).all()
        blackouts = db.query(BlackoutPeriod).filter(
            BlackoutPeriod.lab_id == lab.id,
            BlackoutPeriod.blackout_date == d,
        ).all()

        # 预约与不可约时段合并成统一占用列表，再找该时段内最长的空闲段。
        blocked = sorted(
            [(r.start_time, r.end_time) for r in occupied]
            + [(b.start_time, b.end_time) for b in blackouts]
        )
        free_starts = range_start
        best_free = None
        for block_start, block_end in blocked:
            if block_end <= range_start or block_start >= range_end:
                continue
            gap_start = max(free_starts, range_start)
            gap_end = min(block_start, range_end)
            gap_min = (datetime.combine(d, gap_end) - datetime.combine(d, gap_start)).total_seconds() / 60
            if gap_min >= need_minutes:
                if not best_free or gap_min > best_free[2]:
                    best_free = (gap_start, gap_end, gap_min)
            free_starts = max(free_starts, block_end)
        gap_start = max(free_starts, range_start)
        gap_end = range_end
        gap_min = (datetime.combine(d, gap_end) - datetime.combine(d, gap_start)).total_seconds() / 60
        if gap_min >= need_minutes:
            if not best_free or gap_min > best_free[2]:
                best_free = (gap_start, gap_end, gap_min)

        if best_free:
            # 查这个实验室的设备
            equipments = db.query(Equipment).filter(
                Equipment.lab_id == lab.id, Equipment.status == 1, Equipment.quantity > 0
            ).all()
            equip_text = "、".join(f"{e.name}×{e.quantity}" for e in equipments) or "无"
            start_dt = datetime.combine(d, best_free[0])
            end_dt = start_dt + timedelta(hours=duration_hours)
            results.append(
                f"实验室ID {lab.id}：{lab.name}（{lab.location}，容量{lab.capacity}人）\n"
                f"  可约时段：{best_free[0].strftime('%H:%M')}-{end_dt.strftime('%H:%M')}\n"
                f"  设备：{equip_text}"
            )

    if not results:
        return f"{reservation_date} 在该时段没有实验室能腾出 {duration_hours} 小时连续空位，建议换个时间段。"
    return f"以下实验室在 {reservation_date} {period} 有空位（已为你选好{duration_hours}小时时段）：\n\n" + "\n\n".join(results)


def get_today() -> str:
    """返回今天日期和星期，方便 AI 换算明天/后天。"""
    today = date.today()
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    lines = [f"今天是 {today.isoformat()}（{weekday_names[today.weekday()]}）。"]
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    lines.append(f"明天是 {tomorrow.isoformat()}（{weekday_names[tomorrow.weekday()]}）。")
    lines.append(f"后天是 {day_after.isoformat()}（{weekday_names[day_after.weekday()]}）。")
    return "\n".join(lines)


def list_lab_equipments(db: Session) -> str:
    """查询所有设备。"""
    items = db.query(Equipment).filter(Equipment.status == 1, Equipment.quantity > 0).order_by(Equipment.lab_id, Equipment.id).all()
    if not items:
        return "当前没有登记可用设备。"
    lines = []
    current_lab = None
    for eq in items:
        lab_name = eq.lab.name if eq.lab else f"实验室#{eq.lab_id}"
        if lab_name != current_lab:
            lines.append(f"【{lab_name}】")
            current_lab = lab_name
        lines.append(f"  {eq.name}：{eq.quantity} 台，位置：{eq.location or '-'}")
    return "\n".join(lines)
```

**`run_model_tools`（本课主流程；其余函数见文末附录）：**

```python
def run_model_tools(
    message: str,
    user_id: int,
    db: Session,
    history: list[dict[str, str]] | None = None,
):
    """真实模型通过 Chat Completions Tool Calling 自主选择工具，yield 每个工具的开始/结束事件。

    yield 的是 dict：{"type": "tool_start", "name": ...} / {"type": "tool_end", "name": ..., "result": ...}
    最后 yield {"type": "done", "results": [...]} 带上所有结果。
    """
    if not settings.OPENAI_API_KEY:
        yield {"type": "done", "results": []}
        return
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    # 从数据库查当前用户信息，直接告诉 AI，不用问用户
    from app.models.user import User
    current_user = db.query(User).filter(User.id == user_id).first()
    user_info = f"当前登录用户：{current_user.full_name or current_user.username}（ID:{current_user.id}）" if current_user else f"用户ID:{user_id}"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\n\n【当前用户信息】{user_info}，预约时自动用这个申请人，不要问用户姓名学号。"},
        *(history or [])[-10:],
        {"role": "user", "content": message},
    ]
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )
    tool_calls = response.choices[0].message.tool_calls or []
    tool_results = []
    write_tool_handled = False
    for tool_call in tool_calls:
        name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments or "{}")
        tool_label = {
            "get_today": "换算今天/明天日期",
            "list_open_labs": "查询开放实验室",
            "list_lab_equipments": "查询设备列表",
            "search_lab_docs": "检索知识库",
            "check_lab_availability": "查询实验室占用情况",
            "recommend_lab": "智能推荐实验室",
            "get_my_reservations": "查询我的预约",
            "cancel_reservation": "取消预约",
            "get_latest_announcements": "查询最新公告",
            "create_lab_reservation": "创建预约",
        }.get(name, name)
        yield {"type": "tool_start", "name": name, "label": tool_label}
        if name == "create_lab_reservation" and write_tool_handled:
            result = "本轮已经处理过一次预约请求，没有重复创建。"
        else:
            result = _execute_tool(name, arguments, db, user_id, message)
            if name == "create_lab_reservation":
                write_tool_handled = True
        tool_results.append(result)
        yield {"type": "tool_end", "name": name, "label": tool_label, "result": result}
    yield {"type": "done", "results": tool_results}
```
```

**三道防线：** ① 模型只负责“选工具 + 填参数”，`strict: True` 让它只能产出符合 schema 的 JSON；② 服务端 `has_explicit_reservation_intent(message)` 只认**当前轮**消息，历史里的“帮我预约”不算数；③ `create_lab_reservation` 再走一遍 `ReservationCreate` + `create_reservation_record`，实验室是否开放、预约时间是否已过（含当天开始时间必须晚于当前时间）、有无冲突全部重算。执行时逐个向前端发 `tool_start`/`tool_end`，过程可见。

**验证：** 未配 Key 时 `run_model_tools` 只发一个空的 `done` 事件、不执行模型工具，由本地规则（`local_tool_node`）兜底；配 Key 后问“当前有哪些开放的实验室”，SSE 里出现 `tool_start`/`tool_end` 与 `已调用：…、AI Tool Calling`；连发两次“确认预约”，第二次命中时间冲突而不是生成第二条记录。

## 第 24 节：用 LangGraph 做智能预约 Agent

**知识点清单：** `TypedDict(total=False)` 定义状态、节点是 `state -> state` 的纯函数、`StateGraph` + `add_node` + `set_entry_point` + `add_conditional_edges` + `compile()`、**循环拓扑** `retrieve → agent ⇄ tools → END`（`should_continue` 看最后一条消息里是否还有 `tool_calls`）、没有 Key 时 `agent_node` 退化为 `local_tool_node` 本地规则、缺少 langgraph 时 `ImportError` 降级为顺序调用、`local_tool_node` 的撤回边界、意图识别用 `re.fullmatch`/`re.match` 而非包含判断。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 状态定义 | [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) | `AgentState`（附录完整） |
| 检索节点 | [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) | `retrieve_node`（附录完整） |
| 循环调度 | [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) | `agent_node`、`execute_tools_node`、`should_continue`（见下） |
| 本地工具节点 | [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) | `local_tool_node`（附录完整） |
| 意图与撤回识别 | [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) | `has_explicit_reservation_intent`、`has_cancel_reservation_intent`、`get_user_messages`（附录完整） |
| 建图与执行 | [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) | `build_graph`、`AGENT_GRAPH`、`run_graph`（附录完整） |

**建图与执行（完整函数）：**

```python
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


AGENT_GRAPH, GRAPH_ENGINE = build_graph()


def run_graph(
    message: str,
    user_id: int,
    db: Session,
    history: list[dict[str, str]] | None = None,
) -> AgentState:
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

**两个节点（完整函数）：**

```python
def retrieve_node(state: AgentState) -> AgentState:
    documents, engine = search_documents(state["message"])
    return {"retrieved_docs": documents, "retrieval_engine": engine}
```

```python
def local_tool_node(state: AgentState) -> AgentState:
    """没有模型 Key 时用明确规则选择只读工具。"""
    message = state["message"]
    context = []
    used_tools = ["search_lab_docs"]
    if any(word in message for word in ("实验室", "开放", "设备", "机房")):
        context.append(list_open_labs(state["db"]))
        used_tools.append("list_open_labs")

    pattern = r"预约.*?(?:ID\s*)?(\d+).*?(\d{4}-\d{2}-\d{2}).*?(\d{1,2}:\d{2})\s*[-到至]\s*(\d{1,2}:\d{2}).*?用途[：:]\s*([^\r\n]+)"
    matched = None
    for user_message in reversed(get_user_messages(state)[-2:]):
        if has_cancel_reservation_intent(user_message):
            break
        matched = re.search(pattern, user_message, re.IGNORECASE)
        if matched:
            break
    if matched and not settings.OPENAI_API_KEY and has_explicit_reservation_intent(message):
        arguments = {
            "lab_id": int(matched.group(1)),
            "reservation_date": matched.group(2),
            "start_time": matched.group(3),
            "end_time": matched.group(4),
            "purpose": matched.group(5),
        }
        context.append(create_lab_reservation(state["db"], state["user_id"], arguments))
        used_tools.append("create_lab_reservation")
    elif not settings.OPENAI_API_KEY and has_cancel_reservation_intent(message):
        context.append("已停止本次预约意向，没有创建预约。")
    elif matched and not settings.OPENAI_API_KEY:
        context.append("预约信息已识别；请回复确认预约后再创建预约。")
    return {"tool_context": context, "used_tools": used_tools}
```

**循环工具调用（完整函数）——有 Key 时 `agent` 与 `tools` 通过条件边循环：**

```python
def agent_node(state: AgentState) -> AgentState:
    """图里的 agent 节点：调大模型，拿到回复（可能含 tool_calls）。

    没有配置模型 Key 时退化为本地规则节点（查开放实验室、识别预约格式），
    保证离线模式也能走完同一张图。
    """
    if not settings.OPENAI_API_KEY:
        return local_tool_node(state)

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    messages = state.get("messages") or [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(state.get("history") or [])[-10:],
        {"role": "user", "content": state["message"]},
    ]

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )
    assistant_msg = response.choices[0].message

    if assistant_msg.tool_calls:
        # 有工具要调，把 assistant 消息加进 messages，等 tools_node 执行
        new_messages = messages + [assistant_msg.model_dump()]
        return {"messages": new_messages}
    else:
        # 没有工具要调，就是最终回答
        return {"final_answer": assistant_msg.content or "", "messages": messages}


def execute_tools_node(state: AgentState) -> AgentState:
    """执行 messages 里最后一条 assistant 消息的 tool_calls，结果加回 messages。"""
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    messages = state["messages"]
    last_assistant = messages[-1]

    tool_results = []
    for tc in last_assistant.get("tool_calls", []):
        name = tc["function"]["name"]
        args = json.loads(tc["function"]["arguments"] or "{}")
        result = _execute_tool(name, args, state["db"], state["user_id"], state["message"])
        tool_results.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": result,
        })

    new_messages = messages + tool_results
    return {"messages": new_messages}


def should_continue(state: AgentState) -> str:
    """条件边：最后一条消息有 tool_calls 就继续执行工具，否则结束。"""
    if not settings.OPENAI_API_KEY:
        return "end"
    messages = state.get("messages") or []
    if not messages:
        return "end"
    last = messages[-1]
    if last.get("role") == "assistant" and last.get("tool_calls"):
        return "tools"
    return "end"
```

**意图识别（完整函数）——为什么不能写 `"帮我预约" in message`：**

```python
def has_explicit_reservation_intent(message: str) -> bool:
    normalized_message = "".join(message.lower().split())
    # 明确确认
    if re.fullmatch(
        r"(?:请|麻烦)?(?:确认|确认预约|帮我预约|立即预约|提交预约|创建预约|就这个|选这个|就选这个|可以|行|好的)[。.!！]*",
        normalized_message,
    ):
        return True
    # 直接说选哪个实验室
    if re.search(r"(选|就|要).{0,4}(实验室|id|编号|\d+号)", normalized_message):
        return True
    # 预约开头
    return bool(
        re.match(
            r"^(?:请|麻烦)?(?:帮我|立即|提交|创建)?预约(?:实验室|id|编号|\d)",
            normalized_message,
            re.IGNORECASE,
        )
    )


def has_cancel_reservation_intent(message: str) -> bool:
    normalized_message = "".join(message.lower().split())
    if normalized_message in {"取消", "撤销", "不要", "算了", "先不"}:
        return True
    return bool(
        re.match(r"^(?:我|请|麻烦)?(?:现在|先)?(?:不要|别|不想|不需要|不用|无需|暂不|先不|取消|撤销)", normalized_message)
        and re.search(r"预约|创建|提交|确认", normalized_message)
    )


def get_user_messages(state: AgentState) -> list[str]:
    user_messages = [
        item["content"]
        for item in state.get("history", [])
        if item.get("role") == "user" and item.get("content")
    ]
    return [*user_messages[-10:], state["message"]]
```

**数据流：** `chat_stream` → `run_graph(message, user_id, db, history)` → 建好初始 state → `AGENT_GRAPH.invoke(initial_state)` → `retrieve` 写入 `retrieved_docs`/`retrieval_engine` → `agent`：配了 Key 时调用模型选择工具，没有 Key 时直接执行 `local_tool_node` 本地规则。若模型给出 `tool_calls`，条件边把流程交给 `tools` 执行，执行完**回到 `agent`** 继续判断，直到没有新的工具调用才 `END`。LangGraph 在这里的价值是**拓扑可视化 + 状态显式 + 循环条件分支**。

**验证：** 卸载/未装 langgraph 时 `GRAPH_ENGINE` 显示“顺序编排（安装 langgraph 后自动启用）”，AI 页面功能不变；装好后显示“LangGraph循环工具”；发“不要帮我预约”与“我不想创建预约”，均不得创建记录（`tests/test_api.py::test_ai_confirmation_uses_latest_request_and_respects_cancellation` 覆盖）。

## 第 25 节：用 SSE 流式输出并让过程可见

**知识点清单：** 七种事件 `status`/`tool_start`/`tool_end`/`tool`/`token`/`done`/`error`、`sse_event` 的帧格式、`StreamingResponse` 的 media type 与反代缓冲头、生成器内 `try/except/finally`、异常只记日志不把堆栈发给前端、有 Key 时 Chat Completions `stream=True` 逐 token、无 Key 时 `stream_answer` 按 12 字切片模拟流式的本地兜底、前端按事件名分流。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 事件帧格式 | [`backend/app/api/ai.py`](../../backend/app/api/ai.py) | `sse_event`（第 20 节已贴完整） |
| 事件序列 | [`backend/app/api/ai.py`](../../backend/app/api/ai.py) | `generate_events`（第 20 节已贴完整） |
| 逐 token 生成 | [`backend/app/ai/agent.py`](../../backend/app/ai/agent.py) | `stream_answer`、`build_prompt_context`（附录完整） |
| 前端解析 | [`fronted/src/api/ai.js`](../../fronted/src/api/ai.js) | `handleEventBlock`、`reader.read()` 循环（第 21 节已贴完整） |

**逐 token 生成（完整函数）：**

```python
def build_prompt_context(state: AgentState, model_tool_results: list[str]) -> str:
    document_text = "\n\n".join(
        f"来源：{item.get('source', 'knowledge')}\n{item['text']}" for item in state.get("retrieved_docs", [])
    )
    tool_text = "\n".join(state.get("tool_context", []) + model_tool_results)
    return f"知识库内容：\n{document_text}\n\n系统实时数据/工具结果：\n{tool_text or '无'}"


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

**一次请求的真实事件顺序：**

| 顺序 | 事件 | 数据 | 前端表现 |
| --- | --- | --- | --- |
| 1 | `status` | `正在通过 LangGraph循环工具 分析问题…` | 过程标签 |
| 2 | `status` | `已使用 ChromaDB 完成 RAG 检索` | 过程标签 |
| 3 | `tool_start` / `tool_end` | 模型工具的开始/完成（仅配置 Key 且模型真的选工具时出现） | 过程标签“正在…/✓ …完成” |
| 4 | `tool` | `已调用：search_lab_docs、list_open_labs` | 过程标签（无工具时不发） |
| 5 | `token` | 逐段文本 | 气泡逐字增长 |
| 6 | `done` | `回答完成` | 结束，`sending=false` |
| 异常 | `error` | `AI 助手暂时无法回答，请稍后重试` | 气泡替换为提示文案 |

**为什么 `error` 事件不返回堆栈：** 生成器里的 `except Exception` 只 `logger.exception(...)` 写到后端终端，前端只收到一句中文提示。堆栈含文件路径与配置细节，不适合给浏览器。

**验证：** 用 `curl.exe -N -X POST http://127.0.0.1:8000/api/ai/chat/stream -H "Authorization: Bearer <自己的Token>" -H "Content-Type: application/json" -d "{\"message\":\"实验室预约规则\",\"history\":[]}"` 观察事件顺序；刷新页面时停止请求，后端日志出现 `AI 助手处理失败` 但不影响后续请求。

## 第 26 节：完善系统首页与课程收尾

**知识点清单：** `func.count` / `func.coalesce(func.sum(...), 0)` 聚合、按 `is_superuser` 区分统计口径、`scalar() or 0` 处理空结果、前端 `reactive` 承接统计、`computed` 生成统计卡片、`markRaw` 避免把组件对象变成响应式。

| 知识点 | 完整代码文件 | 实现该知识点的具体代码 |
| --- | --- | --- |
| 统计接口 | [`backend/app/api/stats.py`](../../backend/app/api/stats.py) | `get_summary` |
| 前端接口 | [`fronted/src/api/stats.js`](../../fronted/src/api/stats.js) | `getSummaryApi` |
| 首页 | [`fronted/src/views/home.vue`](../../fronted/src/views/home.vue) | 完整组件（见下） |

**完整源码：**

[`backend/app/api/stats.py`](../../backend/app/api/stats.py)（当前完整内容）：

```python
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User

router = APIRouter(prefix="/stats", tags=["首页统计"])


@router.get("/summary")
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """首页统计：管理员看全局，学生只看自己的预约。"""
    reservation_query = db.query(func.count(Reservation.id))
    pending_query = reservation_query.filter(Reservation.status == "pending")
    if not current_user.is_superuser:
        reservation_query = reservation_query.filter(Reservation.user_id == current_user.id)
        pending_query = pending_query.filter(Reservation.user_id == current_user.id)

    data = {
        "lab_count": db.query(func.count(Lab.id)).filter(Lab.status == 1).scalar() or 0,
        "equipment_count": db.query(func.coalesce(func.sum(Equipment.quantity), 0)).filter(
            Equipment.status == 1
        ).scalar() or 0,
        "reservation_count": reservation_query.scalar() or 0,
        "pending_count": pending_query.scalar() or 0,
    }
    if current_user.is_superuser:
        data["user_count"] = db.query(func.count(User.id)).scalar() or 0
    return Response.success(data=data)
```

[`fronted/src/api/stats.js`](../../fronted/src/api/stats.js)（当前完整内容）：

```js
import request from '@/utils/request'

export function getSummaryApi() {
  return request.get('/api/stats/summary')
}
```

[`fronted/src/views/home.vue`](../../fronted/src/views/home.vue)（完整 `<template>` 与 `<script setup>`；`<style scoped>` 纯 CSS 省略）：

```vue
<template>
  <div class="home-page">
    <section class="welcome-card">
      <div>
        <p class="welcome-label">WELCOME</p>
        <h1>{{ greeting }}，{{ displayName }}</h1>
        <p>在这里查看实验室、设备和预约进度，也可以让 AI 助手帮你查询与预约。</p>
      </div>
      <el-button type="primary" @click="$router.push('/chat')">咨询 AI 助手</el-button>
    </section>

    <section v-loading="loadingValue" class="stats-grid">
      <article v-for="item in statItems" :key="item.key" class="stat-card" :class="{ clickable: item.path }" @click="goTo(item.path)">
        <div class="stat-icon" :style="{ background: item.color }">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div>
          <p>{{ item.label }}</p>
          <strong>{{ summary[item.key] ?? 0 }}</strong>
        </div>
        <el-icon v-if="item.path" class="stat-arrow"><ArrowRight /></el-icon>
      </article>
    </section>

    <section class="guide-card">
      <h2>预约流程</h2>
      <el-steps :active="1" align-center>
        <el-step title="选择实验室" description="查看开放状态与设备" />
        <el-step title="提交预约" description="填写日期、时间与用途" />
        <el-step title="等待审核" description="管理员处理预约申请" />
        <el-step title="按时使用" description="审核通过后前往实验室" />
      </el-steps>
    </section>
  </div>
</template>

<script setup>
import { computed, markRaw, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Calendar, Collection, Monitor, User } from '@element-plus/icons-vue'
import { getSummaryApi } from '@/api/stats'
import { useUser } from '@/utils/user'

const router = useRouter()
const { userInfo, isAdmin } = useUser()
const loadingValue = ref(false)
const summary = reactive({})
const displayName = computed(() => userInfo.value?.full_name || userInfo.value?.username || '同学')

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '上午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

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

const goTo = (path) => {
  if (path) router.push(path)
}

onMounted(async () => {
  loadingValue.value = true
  try {
    const res = await getSummaryApi()
    Object.assign(summary, res.data)
  } finally {
    loadingValue.value = false
  }
})
</script>
```

**注意 `markRaw`：** 图标是组件对象。不包 `markRaw` 会把它变成响应式代理，Vue 会警告“组件被做成响应式对象”，也带来无谓开销。`user_count` 只在管理员响应里存在，学生端模板用 `summary[item.key] ?? 0` 兜底。

**验证：** 学生首页“待审核预约”只统计自己的；用管理员登录多出“系统用户”卡片且数字等于 `users` 表行数；停用一个实验室，`lab_count` 立即减 1。

## 第 27 节：项目图解与完整链路复盘

本课不引入新代码，把 00–26 节的落点串成一条链。

**（1）一次 AI 提问的完整链路**

```
chat.vue sendMessage() → store chat.js sendMessage()
  └─ api/ai.js streamChatApi()                       fetch + AbortController
       └─ POST /api/ai/chat/stream                   Authorization: Bearer <JWT>
            ├─ schemas/ai.py  ChatRequest            校验 message/history/role
            ├─ dependencies/auth.py get_current_user 解 JWT → 查 user → 验 password_version
            ├─ api/ai.py sse_event("status", …)      第 1 条事件
            ├─ ai/agent.py run_graph()               LangGraph: retrieve → agent ⇄ tools
            │    ├─ retrieve_node → ai/knowledge.py search_documents()
            │    │      └─ sync_collection（按块增/改/删增量同步）→ ChromaDB
            │    │         异常时降级 simple_search
            │    ├─ agent_node（有 Key → 模型选工具；无 Key → 本地规则）
            │    │      └─ local_tool_node → ai/tools.py list_open_labs()
            │    └─ execute_tools_node（有 tool_calls 时执行后回到 agent）
            ├─ ai/agent.py run_model_tools()          有 Key 时逐个发 tool_start/tool_end
            │    └─ _execute_tool → ai/tools.py create_lab_reservation()
            │         └─ services/reservation.py create_reservation_record()
            │             ├─ with_for_update() 锁实验室行
            │             ├─ 开放状态 / 当天时间 / 每周上限 / 冲突检查
            │             └─ db.commit() → reservations 表
            ├─ ai/agent.py build_prompt_context()     知识库 + 工具结果
            ├─ ai/agent.py stream_answer()            有 Key 逐 token / 无 Key 本地答案
            └─ api/ai.py sse_event("token"/"done") → StreamingResponse
       └─ api/ai.js handleEventBlock()               拆分 event:/data:
            └─ store chat.js 更新 messages            逐 token 渲染、过程标签累积
```

**（2）四份教程的落点索引**

| 教程文件 | 覆盖节 | 主要产出 |
| --- | --- | --- |
| [`00-08-foundation.md`](00-08-foundation.md) | 00–08 | 工程骨架、路由、布局、模型基类、JWT 登录、统一响应、axios 封装 |
| [`09-14-users.md`](09-14-users.md) | 09–14 | 注册、上传、个人资料、改密、用户管理、`user.vue` |
| [`15-19-business.md`](15-19-business.md) | 15–19 | 实验室、设备、预约、审核、`services/reservation.py` |
| `20-27-ai.md`（本文） | 20–27 | AI 对话、RAG、Tool Calling、LangGraph、SSE、首页统计 |

**（3）安全边界（全链路复核）**

- 密钥只写在 `backend/.env`；`VITE_` 变量会被打进浏览器产物，**不能**放密钥。
- 密码存 bcrypt 哈希，响应体从不含密码；AI 上下文也不拼装密码字段。
- 写操作三重确认：模型只填参数 → 服务端校验当前轮意图 → Service 重算全部业务规则。
- 知识库与工具结果只作为**数据**拼进 prompt；系统提示明确要求不得编造实验室与预约状态。
- `CORS` 只放行本机前端源；上传按魔数嗅探真实类型并限制 5MB。

**（4）验证清单（不依赖真实模型 Key）**

```bash
cd backend && python -m unittest discover -s tests -v
cd fronted && npm run build
```

两条命令应全部通过：`tests/test_api.py` 覆盖注册登录、越权 403、实验室/设备/预约全流程、上传魔数校验与 AI SSE（含“确认预约”多轮只生成一条记录），`tests/test_knowledge.py` 覆盖索引增改删同步与降级。**测试使用系统临时目录，不会改动开发 MySQL 数据与项目自带知识文件。**

## 本组自检

- 能说出 `db` 为什么必须在生成器内部创建，而不是用 `Depends(get_db)`。
- 能解释 128 维向量是怎么算出来的、为什么要按段落分块，以及为什么用 SHA-256 内容指纹而不是文件时间。
- 能说明写工具的“三道防线”，以及为什么不能只依赖模型判断。
- 能画出 `status → status →（tool_start → tool_end）→ tool → token → done` 的事件顺序并对应到前端表现。
- 能指出 `markRaw`（首页统计图标）与 Pinia store（对话状态跨页面保留）分别解决什么问题，以及 `should_continue` 如何让 `agent` 与 `tools` 形成循环。

## 附录：`backend/app/ai/agent.py` 完整源码

第 23、24、25 节引用的函数都在这个文件里，以下为当前完整内容：

```python
import json
import re
from typing import Any, TypedDict

from openai import OpenAI
from sqlalchemy.orm import Session

from app.ai.knowledge import search_documents
from app.ai.tools import (
    TOOL_SCHEMAS,
    cancel_reservation,
    check_lab_availability,
    create_lab_reservation,
    get_latest_announcements,
    get_my_reservations,
    get_today,
    list_lab_equipments,
    list_open_labs,
    recommend_lab,
)
from app.config import settings


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


def has_explicit_reservation_intent(message: str) -> bool:
    normalized_message = "".join(message.lower().split())
    # 明确确认
    if re.fullmatch(
        r"(?:请|麻烦)?(?:确认|确认预约|帮我预约|立即预约|提交预约|创建预约|就这个|选这个|就选这个|可以|行|好的)[。.!！]*",
        normalized_message,
    ):
        return True
    # 直接说选哪个实验室
    if re.search(r"(选|就|要).{0,4}(实验室|id|编号|\d+号)", normalized_message):
        return True
    # 预约开头
    return bool(
        re.match(
            r"^(?:请|麻烦)?(?:帮我|立即|提交|创建)?预约(?:实验室|id|编号|\d)",
            normalized_message,
            re.IGNORECASE,
        )
    )


def has_cancel_reservation_intent(message: str) -> bool:
    normalized_message = "".join(message.lower().split())
    if normalized_message in {"取消", "撤销", "不要", "算了", "先不"}:
        return True
    return bool(
        re.match(r"^(?:我|请|麻烦)?(?:现在|先)?(?:不要|别|不想|不需要|不用|无需|暂不|先不|取消|撤销)", normalized_message)
        and re.search(r"预约|创建|提交|确认", normalized_message)
    )


def get_user_messages(state: AgentState) -> list[str]:
    user_messages = [
        item["content"]
        for item in state.get("history", [])
        if item.get("role") == "user" and item.get("content")
    ]
    return [*user_messages[-10:], state["message"]]


def local_tool_node(state: AgentState) -> AgentState:
    """没有模型 Key 时用明确规则选择只读工具。"""
    message = state["message"]
    context = []
    used_tools = ["search_lab_docs"]
    if any(word in message for word in ("实验室", "开放", "设备", "机房")):
        context.append(list_open_labs(state["db"]))
        used_tools.append("list_open_labs")

    pattern = r"预约.*?(?:ID\s*)?(\d+).*?(\d{4}-\d{2}-\d{2}).*?(\d{1,2}:\d{2})\s*[-到至]\s*(\d{1,2}:\d{2}).*?用途[：:]\s*([^\r\n]+)"
    matched = None
    for user_message in reversed(get_user_messages(state)[-2:]):
        if has_cancel_reservation_intent(user_message):
            break
        matched = re.search(pattern, user_message, re.IGNORECASE)
        if matched:
            break
    if matched and not settings.OPENAI_API_KEY and has_explicit_reservation_intent(message):
        arguments = {
            "lab_id": int(matched.group(1)),
            "reservation_date": matched.group(2),
            "start_time": matched.group(3),
            "end_time": matched.group(4),
            "purpose": matched.group(5),
        }
        context.append(create_lab_reservation(state["db"], state["user_id"], arguments))
        used_tools.append("create_lab_reservation")
    elif not settings.OPENAI_API_KEY and has_cancel_reservation_intent(message):
        context.append("已停止本次预约意向，没有创建预约。")
    elif matched and not settings.OPENAI_API_KEY:
        context.append("预约信息已识别；请回复确认预约后再创建预约。")
    return {"tool_context": context, "used_tools": used_tools}


# ========== LangGraph 图内循环工具调用 ==========

SYSTEM_PROMPT = (
    "你是智能实验室预约助手。严格遵守：\n"
    "1. 绝对不要问用户'你是谁'、'你的姓名'、'学号'——系统已经告诉你了\n"
    "2. 绝对不要问用户要时间段、人数——这些调 recommend_lab 工具自动查\n"
    "3. 用户说想做实验/要预约时，必须先调 get_today 和 recommend_lab 工具，不许自己瞎编实验室和时间\n"
    "4. recommend_lab 返回的每个选项包含：实验室ID、名称、可约时间段、设备\n"
    "5. 把选项列给用户选（比如'1号实验室14:00-16:00，2号实验室15:00-17:00'）\n"
    "6. 用户说'选1号'、'就这个'、'确认'后，直接调 create_lab_reservation，把 lab_id、日期、开始结束时间填好\n"
    "7. purpose 用途根据用户说的内容自动填，不要问用户\n"
    "8. 创建成功后告诉用户预约编号和状态即可"
)


def _execute_tool(name: str, arguments: dict, db: Session, user_id: int, message: str) -> str:
    """执行单个工具，返回结果字符串。"""
    if name == "list_open_labs":
        return list_open_labs(db)
    if name == "search_lab_docs":
        documents, _ = search_documents(arguments.get("query", message))
        return "\n".join(item["text"] for item in documents)
    if name == "get_my_reservations":
        return get_my_reservations(db, user_id, arguments.get("status"))
    if name == "cancel_reservation":
        return cancel_reservation(db, user_id, int(arguments["reservation_id"]))
    if name == "check_lab_availability":
        return check_lab_availability(db, int(arguments["lab_id"]), arguments["reservation_date"])
    if name == "get_latest_announcements":
        return get_latest_announcements(db)
    if name == "recommend_lab":
        return recommend_lab(db, arguments["reservation_date"], arguments.get("period", "afternoon"), int(arguments.get("duration_hours", 2)))
    if name == "get_today":
        return get_today()
    if name == "list_lab_equipments":
        return list_lab_equipments(db)
    if name == "create_lab_reservation":
        if not has_explicit_reservation_intent(message):
            return "预约参数已识别，请用户明确回复确认预约后再创建。"
        return create_lab_reservation(db, user_id, arguments)
    return f"未知工具：{name}"


def agent_node(state: AgentState) -> AgentState:
    """图里的 agent 节点：调大模型，拿到回复（可能含 tool_calls）。

    没有配置模型 Key 时退化为本地规则节点（查开放实验室、识别预约格式），
    保证离线模式也能走完同一张图。
    """
    if not settings.OPENAI_API_KEY:
        return local_tool_node(state)

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    messages = state.get("messages") or [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(state.get("history") or [])[-10:],
        {"role": "user", "content": state["message"]},
    ]

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )
    assistant_msg = response.choices[0].message

    if assistant_msg.tool_calls:
        # 有工具要调，把 assistant 消息加进 messages，等 tools_node 执行
        new_messages = messages + [assistant_msg.model_dump()]
        return {"messages": new_messages}
    else:
        # 没有工具要调，就是最终回答
        return {"final_answer": assistant_msg.content or "", "messages": messages}


def execute_tools_node(state: AgentState) -> AgentState:
    """执行 messages 里最后一条 assistant 消息的 tool_calls，结果加回 messages。"""
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    messages = state["messages"]
    last_assistant = messages[-1]

    tool_results = []
    for tc in last_assistant.get("tool_calls", []):
        name = tc["function"]["name"]
        args = json.loads(tc["function"]["arguments"] or "{}")
        result = _execute_tool(name, args, state["db"], state["user_id"], state["message"])
        tool_results.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": result,
        })

    new_messages = messages + tool_results
    return {"messages": new_messages}


def should_continue(state: AgentState) -> str:
    """条件边：最后一条消息有 tool_calls 就继续执行工具，否则结束。"""
    if not settings.OPENAI_API_KEY:
        return "end"
    messages = state.get("messages") or []
    if not messages:
        return "end"
    last = messages[-1]
    if last.get("role") == "assistant" and last.get("tool_calls"):
        return "tools"
    return "end"


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


AGENT_GRAPH, GRAPH_ENGINE = build_graph()


def run_graph(
    message: str,
    user_id: int,
    db: Session,
    history: list[dict[str, str]] | None = None,
) -> AgentState:
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


def run_model_tools(
    message: str,
    user_id: int,
    db: Session,
    history: list[dict[str, str]] | None = None,
):
    """真实模型通过 Chat Completions Tool Calling 自主选择工具，yield 每个工具的开始/结束事件。

    yield 的是 dict：{"type": "tool_start", "name": ...} / {"type": "tool_end", "name": ..., "result": ...}
    最后 yield {"type": "done", "results": [...]} 带上所有结果。
    """
    if not settings.OPENAI_API_KEY:
        yield {"type": "done", "results": []}
        return
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    # 从数据库查当前用户信息，直接告诉 AI，不用问用户
    from app.models.user import User
    current_user = db.query(User).filter(User.id == user_id).first()
    user_info = f"当前登录用户：{current_user.full_name or current_user.username}（ID:{current_user.id}）" if current_user else f"用户ID:{user_id}"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\n\n【当前用户信息】{user_info}，预约时自动用这个申请人，不要问用户姓名学号。"},
        *(history or [])[-10:],
        {"role": "user", "content": message},
    ]
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )
    tool_calls = response.choices[0].message.tool_calls or []
    tool_results = []
    write_tool_handled = False
    for tool_call in tool_calls:
        name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments or "{}")
        tool_label = {
            "get_today": "换算今天/明天日期",
            "list_open_labs": "查询开放实验室",
            "list_lab_equipments": "查询设备列表",
            "search_lab_docs": "检索知识库",
            "check_lab_availability": "查询实验室占用情况",
            "recommend_lab": "智能推荐实验室",
            "get_my_reservations": "查询我的预约",
            "cancel_reservation": "取消预约",
            "get_latest_announcements": "查询最新公告",
            "create_lab_reservation": "创建预约",
        }.get(name, name)
        yield {"type": "tool_start", "name": name, "label": tool_label}
        if name == "create_lab_reservation" and write_tool_handled:
            result = "本轮已经处理过一次预约请求，没有重复创建。"
        else:
            result = _execute_tool(name, arguments, db, user_id, message)
            if name == "create_lab_reservation":
                write_tool_handled = True
        tool_results.append(result)
        yield {"type": "tool_end", "name": name, "label": tool_label, "result": result}
    yield {"type": "done", "results": tool_results}


def build_prompt_context(state: AgentState, model_tool_results: list[str]) -> str:
    document_text = "\n\n".join(
        f"来源：{item.get('source', 'knowledge')}\n{item['text']}" for item in state.get("retrieved_docs", [])
    )
    tool_text = "\n".join(state.get("tool_context", []) + model_tool_results)
    return f"知识库内容：\n{document_text}\n\n系统实时数据/工具结果：\n{tool_text or '无'}"


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


---
