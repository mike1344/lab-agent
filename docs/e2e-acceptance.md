# 浏览器端到端验收（E2E）

> 场景：学生修改待审核预约 → 教师审核通过 → 学生看到“已通过”  
> 脚本：`fronted/scripts/e2e-reservation.mjs`  
> 数据：`backend/scripts/seed_e2e.py`

## 1. 为什么单独起 8002/5174

开发机上 8000 可能被其他项目占用，5173 也常被日常开发占用。E2E 使用独立端口，并关闭验证码/限流/调度器，保证可重复：

- 后端：`http://127.0.0.1:8002`
- 前端：`http://127.0.0.1:5174`
- 数据库：本地 MySQL（与日常开发共用，E2E 只清理自己的实验室数据）

## 2. 准备数据

```powershell
cd F:\fastapi项目实战\lab_agent\backend
.\.venv\Scripts\python.exe scripts\seed_e2e.py
```

输出会给出固定账号：

```text
学生：e2e_student / E2eStudent123!
教师：e2e_teacher / E2eTeacher123!
管理员：e2e_admin / E2eAdmin123!
实验室：E2E 演示实验室
```

脚本幂等：重复执行会删除并重建 E2E 实验室的预约，不影响其他实验室。

## 3. 启动 E2E 服务

**终端 1：后端**

```powershell
cd F:\fastapi项目实战\lab_agent\backend
$env:LOGIN_CAPTCHA_ENABLED="false"
$env:RATE_LIMIT_ENABLED="false"
$env:SCHEDULER_ENABLED="false"
$env:CORS_ORIGINS="http://127.0.0.1:5174,http://localhost:5174"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8002
```

**终端 2：前端**

```powershell
cd F:\fastapi项目实战\lab_agent\fronted
$env:VITE_API_BASE_URL="http://127.0.0.1:8002"
npm run dev -- --port 5174 --host 127.0.0.1
```

## 4. 执行

```powershell
cd F:\fastapi项目实战\lab_agent\fronted
$env:BASE_URL="http://127.0.0.1:5174"
node scripts\e2e-reservation.mjs
```

正常输出：

```text
saved 11-e2e-student-pending.png
saved 12-e2e-teacher-review.png
saved 13-e2e-approved.png
E2E PASSED: 学生修改 → 教师通过 → 学生看到已通过，无页面错误
```

## 5. 断言覆盖

1. 学生用 `e2e_student` 登录，打开「我的预约」，找到 `E2E 演示实验室` 的待审核记录；
2. 点击「修改」，修改用途并保存，出现「预约已修改」；
3. 教师用 `e2e_teacher` 登录，在「预约审核」中找到该学生/实验室的记录，点击「通过」；
4. 审核完成，出现「预约审核完成」；
5. 学生刷新页面，记录状态变为「已通过」；
6. 全程监听 `pageerror`、`console.error`、失败请求（忽略 WebSocket 重连噪声），要求为 0。

截图证据：

- `docs/visual-check/11-e2e-student-pending.png`
- `docs/visual-check/12-e2e-teacher-review.png`
- `docs/visual-check/13-e2e-approved.png`

## 6. 定位

这是**本地验收脚本，不进入 CI**：它需要真实 MySQL、可启动的前后端和系统 Chrome，和当前 CI（SQLite + 无浏览器）职责不同。CI 继续跑后端 42 个回归测试、前端 7 个单测、迁移校验和镜像构建；E2E 用于答辩/发布前人工或脚本复验。