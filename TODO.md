# lab_agent 功能优化待做清单

> 生成时间：2026-10-20
> 依据：对比 GitHub 上同类实验室/预约系统的功能面，结合本仓库现有代码核实后整理。
>
> 2026-10-28 更新：发布收尾完成（PR #1 squash 至 master `95635be`，三端 CI 全绿）；
> 多级审批流（36）与 AI 工具审计留存（29 补充）已完成并合并（PR #2 → `217d823`）。
> RAG 补充稠密向量拒答门槛：BGE 可选路径在固定评估集上拒答率 1.0（默认仍为 local；PR #3 → `ebf24d1`）。
> Agent 工具超时：读工具 10 秒硬超时 + 断连跳过后续工具；写工具为事务一致性不强制中断（P2-7 部分完成，PR #4 → `0039eb4`）。
> 解决方案材料：知识库扩到 10 篇、评估集 40 题，BGE 拒答率 1.0；新增 `docs/ai-solution-brief.md` 与 RAG 评估报告。

## 一、对标项目

| 项目 | 技术栈 | Stars | 借鉴点 |
| --- | --- | --- | --- |
| [zongjixiaoai66/LaboratoryManagementSystem](https://github.com/zongjixiaoai66/LaboratoryManagementSystem) | Vue + SpringBoot | 29 | 实验课程、公告/课程评论、收藏、采购记录、三角色 |
| [chenbin2896/lab](https://github.com/chenbin2896/lab) | SpringBoot + AngularJS | 69 | 仪器设备操作配置说明（设备绑定文档展示） |
| [marspal-ai/Laboratory-reservation](https://github.com/marspal-ai/Laboratory-reservation) | Java（2025 新项目） | 9 | 安全准入考试、门禁联动（人脸/刷卡/二维码）、图形化选室、工位级预约、课表冲突校验、多维导出 |
| [shencang/ICRS](https://github.com/shencang/ICRS) + [icrs-vue](https://github.com/shencang/icrs-vue) | Java + Vue | 52 | 日历/视图化占用展示、刷卡签到核销 |
| [mizhexiaoxiao/vue-fastapi-admin](https://github.com/mizhexiaoxiao/vue-fastapi-admin) | FastAPI + Vue3 + Naive UI | 2.3k | RBAC 动态菜单/按钮级权限、审计日志、登录安全 |
| [insistence/RuoYi-FastAPI](https://github.com/insistence/RuoYi-FastAPI) | FastAPI + Vue/React | 1.5k | 定时任务、操作日志、数据字典、代码生成 |
| [garylife/labReservation](https://github.com/garylife/labReservation) | Java Web + ECharts | 27 | 统计图表可视化 |

## 二、现有功能盘点（已核实，勿重复开发）

- 用户：注册/登录/JWT/资料/密码/头像上传；管理员用户 CRUD；**教师角色已有**（`is_teacher`）
- 业务：实验室与设备 CRUD、不可约时段、预约（冲突校验/我的预约/取消/审核）、公告、报修、通知（30 秒轮询未读数）
- 数据：预约记录 Excel 导出（`api/reservation.py` `/export`，openpyxl）；首页 4~5 项数字统计（`api/stats.py`）
- AI：ChromaDB RAG + LangGraph + 10 个工具 + SSE 流式
- 工程化：Alembic 迁移、Docker Compose 一键部署 + Nginx、`/health` 探活、SQLite 回归测试

## 三、待做清单

### P0 —— 高价值、贴合现有架构，建议先做

- [x] **1. 预约日历视图（周/日视图）** ✅ 2026-10-20 已完成
  - 后端：`GET /api/reservations/calendar`（`api/reservation.py`），返回一段日期内的预约占用与不可约时段，缺省当前周（周一起始），单次最多 31 天；配套回归测试 `test_reservation_calendar_returns_range_events_and_blackouts`。
  - 前端：`lab.vue` 新增「查看周历」弹窗，支持周/日切换、上一周/下一周导航、当前时间红线、重叠预约并排分道；点击空白时段直接预填预约弹窗。
- [x] **2. 首页统计可视化（ECharts）** ✅ 2026-10-21 已完成
  - 后端：`GET /api/stats/dashboard`（`api/stats.py`），一次返回预约趋势（按创建日+状态分组、缺天补零）、实验室使用排行 Top8、报修状态分布；教师/管理员看全局，学生只看自己的数据；days 参数 1~90 收敛。
  - 前端：`home.vue` 引入 echarts（按需注册 BarChart/PieChart），趋势堆叠柱状图（7/30 天切换）、横向条形排行、环形报修分布；窗口 resize 自适应，卸载时 dispose；配套回归测试 `test_stats_dashboard_returns_trend_usage_and_repairs`。
- [x] **3. 定时任务：过期预约自动处理 + 开课前提醒** ✅ 2026-10-21 已完成
  - 后端：新增 `services/schedule.py`（APScheduler 3.11，5 分钟周期 + 启动即执行一轮）：
    - `expire_stale_reservations`：结束时间已过且仍 pending/approved 的预约自动置为 `expired` 并发站内通知；
    - `remind_upcoming_reservations`：开始前 60 分钟内的已通过预约发提醒，以 notification(type+related_id) 存在性做幂等去重，不新增表字段。
  - 接线：`main.py` 改用 FastAPI lifespan 启停调度器；`config.py` 新增 `SCHEDULER_ENABLED` 开关（测试环境设为 false 避免后台线程干扰断言；多副本部署时只开一个实例）。
  - 配套：预约状态新增 `expired`（无表结构变更，无需迁移），前端 `reservation.vue` 状态标签、`home.vue` 趋势图、后端 `/stats/dashboard` 趋势桶同步支持；回归测试 `test_scheduler_expires_stale_and_reminds_upcoming`。
- [x] **4. 通知实时化（WebSocket）** ✅ 2026-10-21 已完成
  - 后端：新增 `api/ws.py` 的 `WS /api/ws/notifications` 端点（JWT 走 `?token=` 查询参数——浏览器 WS 无法自定义请求头；校验链与 `get_current_user` 一致，改密后旧 token 立即失效）；`services/ws.py` 的 `ConnectionManager` 按 user_id 分组连接，借连接建立时记录的事件循环 `run_coroutine_threadsafe` 从线程池/调度线程安全推送。审核通过/驳回（`api/reservation.py`）、报修处理（`api/repair.py`）、定时任务的过期关闭与开课提醒（`services/schedule.py`）四处通知落库后同步实时推送。
  - 前端：新增 `utils/ws.js`（25 秒心跳、指数退避重连 3s→60s 封顶、4401 鉴权失败不重连）；`layouts.vue` 收到推送即弹 ElNotification 并跳转对应页面，未读数以服务端为准拉取；WebSocket 在线时暂停 30 秒轮询，掉线自动恢复——轮询保留为降级兜底（多 worker 部署时推送按进程隔离，兜底尤其必要）。
  - 部署：`nginx.conf` 新增 `/api/ws/` 独立 location（Upgrade/Connection 升级头 + 1 小时读超时）；`docker-compose.yml` 默认 `SCHEDULER_ENABLED=false`（2 个 worker 会各跑一份调度器重复发通知），`start_scheduler` 检测到多进程时打告警日志。
  - 配套：回归测试 `test_websocket_pushes_review_result_and_rejects_bad_token`（真实连接断言审核结果实时到达 + 非法 token 以 4401 关闭），20 个测试全部通过。
- [x] **5. 登录安全加固** ✅ 2026-10-21 已完成
  - 参考：vue-fastapi-admin
  - 后端：新增 `services/login_security.py`（线程安全内存实现）：
    - 图形验证码：`captcha` 库（Pillow 绘图，内置字体）生成 4 位 PNG，`GET /api/auth/captcha` 返回 base64 data URL + `captcha_id`；**一次性消费**——校验后无论对错立即从内存删除，5 分钟过期，`hmac.compare_digest` 常量时间比较。
    - 失败锁定：滑动窗口统计，15 分钟内连续失败 5 次即锁定，锁定期内正确密码也返回 403；登录成功清空计数，账号被禁用不计入失败。
    - 登录日志：新增 `login_logs` 表（`models/login_log.py` + Alembic 迁移 `9f2e7c4d8a16`），成功/失败都落库（用户名、user_id、IP（优先取 `X-Forwarded-For` 首段）、UA、结果说明）；管理员可查 `GET /api/auth/login-logs`（倒序分页 + 用户名过滤）。
    - 接线：登录校验顺序为「锁定检查 → 验证码 → 密码」，验证码放在密码校验之前防止绕过；`config.py` 新增 `LOGIN_CAPTCHA_ENABLED` / `LOGIN_MAX_FAILURES` / `LOGIN_LOCKOUT_MINUTES` / `CAPTCHA_EXPIRE_MINUTES` 四个配置项，`.env.example` 同步说明。
  - 前端：`login.vue` 验证码行（点击图片刷新、登录失败自动换一张、`enabled=false` 时隐藏），`api/auth.js` 新增 `getCaptchaApi`。
  - 配套：回归测试 `test_login_captcha_lockout_and_audit_log` 覆盖验证码错误/缺失/一次性消费、5 次失败锁定、成功解锁、日志落库与管理员/普通用户权限差异；测试环境以 `LOGIN_CAPTCHA_ENABLED=false` 保持其余用例直接登录，21 个测试全部通过。
  - 已知限制：失败计数为内存态——进程重启清零，多 worker（`WEB_CONCURRENCY>1`）时各进程独立计数（锁定阈值按进程各算各的）；需要全局精确控制时可把存储层换成 Redis（接口不变）。
- [x] **6. 操作日志（审计）** ✅ 2026-10-21 已完成
  - 参考：vue-fastapi-admin / RuoYi-FastAPI
  - 后端：新增 `models/operation_log.py` + Alembic 迁移 `a3d5f7b9c1e2`（`operation_logs` 表：操作人、方法、路径、操作说明、成败、HTTP 状态码、结果信息、IP、耗时）；`middleware/operation_log.py` 的 ASGI 中间件统一拦截所有写请求（POST/PUT/PATCH/DELETE），从 JWT 解析操作人（非法凭证/未登录也留痕），读路由 docstring 首行作为中文操作说明，缓冲 JSON 响应体解析统一信封的业务码与提示，未捕获异常按失败记录后继续上抛。
  - 排除项：登录/注册（已由 `login_logs` 覆盖）、AI 流式对话与 WS（流式响应不做缓冲）、`/uploads` 静态资源；中间件注册在 CORS 之前，保证 CORS 是外层、预检请求不进入审计。
  - 查询接口：`GET /api/operation-logs`（管理员，倒序分页，支持操作人模糊/方法/结果过滤），与 user 列表同构返回 `list/total/page/page_size`。
  - 前端：新增 `views/oplog.vue`（筛选栏 + 表格：时间/操作人/角色/方法/操作说明/接口/结果/状态码/说明/IP/耗时 + 分页），`api/operationLog.js`，路由 `/oplog`，侧边菜单仅管理员可见。
  - 配套：回归测试 `test_operation_log_records_writes_and_guards_access` 覆盖「读操作不记录、成功写操作落库（含 docstring 说明与管理员标识）、失败写操作落库（400 + 消息）、学生查询 403、管理员过滤查询」，22 个测试全部通过。
  - 设计取舍：审计是旁路——中间件用独立 `SessionLocal`，写日志失败只打告警不影响接口结果；请求体不落库（避免密码等敏感字段入库），「改了什么」由接口路径与操作说明表达。

### P1 —— 同类系统普遍具备的业务增强

- [x] **7. 设备绑定操作说明/文档** ✅ 2026-10-21 已完成
  - 参考：chenbin2896/lab「仪器设备操作配置说明」
  - 后端：`equipment` 表新增 `usage_doc_url`（String(500)，Alembic 迁移 `c4e6a8d0f2b5`）；`schemas/equipment.py` 增加链接规范化与白名单校验——只允许 `http(s)://` 外链或以 `/` 开头的站内路径（如上传目录 PDF），拒绝 `javascript:` 等危险协议，空字符串视为清空；`equipment_to_dict` 与列表/创建/更新接口全部透出该字段。
  - 前端：`equ.vue` 设备表格新增「操作说明」列（未设置显示占位），点击「查看说明」弹出 760px 详情弹窗，用 iframe 内嵌预览 PDF/网页，并提供「在新窗口打开」兜底（部分站点禁止 iframe 嵌入）；管理端新增/编辑表单增加「操作说明」链接输入框。
  - 配套：回归测试 `test_equipment_usage_doc_url_roundtrip` 覆盖创建/列表/更新往返、站内路径、空串清空与危险协议拒绝，23 个测试全部通过。
  - AI 知识库：外部链接不做抓取索引（避免爬虫与内容漂移）；如需 AI 也能检索某设备手册，把 Markdown 版本放入 `backend/app/knowledge/` 即可——该目录按 `*.md` 自动进 RAG（`ai/knowledge.py`），无需改代码。
- [x] **8. 公告评论 / 已读回执** ✅ 2026-10-21 已完成
  - 参考：zongjixiaoai66 公告评论（Discussgonggaoxinxi）
  - 后端：新增 `announcement_comments` / `announcement_reads` 两张表（Alembic 迁移 `e5f7b9c1d3a4`）：
    - 评论：`parent_id` 自关联实现一层回复，接口拒绝回复"回复"（防止无限嵌套）；`GET/POST /api/announcements/{id}/comments`，`DELETE /api/announcements/comments/{comment_id}`（作者本人或管理员可删，删一级评论连带删除其回复）；返回带评论人姓名/头像。
    - 已读回执：`(announcement_id, user_id)` 唯一约束保证幂等；`POST /api/announcements/{id}/read` 重复调用不重复计数；列表/详情一次查出 `is_read` 与 `read_count`（批量 `IN` + `GROUP BY`，避免 N+1）；`GET /api/announcements/{id}/read-receipts` 管理员查看已读人数/在册人数/已读名单（含首次阅读时间，取回执的 create_time）。
    - 删除公告时应用层级联清理评论与回执，避免孤儿数据。
  - 前端：公告列表标题列显示「未读」标记；详情弹窗新增正文元信息（已读状态、已读人数、查看回执按钮）、评论列表（一级 + 回复缩进）、评论输入框（选填回复对象时自动切换成「回复 @xxx」并支持取消）；管理员多一个已读回执弹窗（已读/在册人数 + 阅读时间列表）。
  - 配套：回归测试 `test_announcement_comments_and_read_receipts` 覆盖未读→已读幂等、二级评论、回复回复被拒、删除权限（403）、管理员回执统计、删除公告级联清理，24 个测试全部通过。
- [x] **9. 收藏实验室 / 设备** ✅ 2026-10-21 已完成
  - 参考：zongjixiaoai66 Storeup 模块
  - 后端：新增 `favorites` 表（Alembic 迁移 `f6a8c2e4d0b7`，`user_id + target_type + target_id` 唯一约束防重复收藏）；`GET /api/favorites`（可按 lab/equipment 过滤，目标已删除的收藏自动隐藏并回填名称/状态）、`POST /api/favorites`（幂等）、`DELETE /api/favorites/{id}`（只能删自己的，别人的按不存在处理）；`/api/labs` 与 `/api/equipment` 列表新增 `favorite_only` 过滤（数据库子查询，不拉全表再筛）。
  - 前端：`lab.vue` / `equ.vue` 每行新增星标按钮（⭐/☆ 切换收藏），工具栏新增「只看收藏」开关；`api/favorite.js` 封装三个接口。
  - 配套：回归测试 `test_favorites_and_favorite_only_filters` 覆盖幂等收藏、类型过滤、收藏列表名称回填、favorite_only 过滤、越权删除保护、取消收藏，25 个测试全部通过。
  - 说明：「我的收藏」以列表过滤方式内嵌在实验室/设备页，不单独开页面——学生进实验室页勾选「只看收藏」即可快速预约，入口更短。
- [x] **10. 设备采购记录** ✅ 2026-10-21 已完成
  - 参考：zongjixiaoai66 采购记录（Caigoujilu）
  - 后端：新增 `procurements` 表（Alembic 迁移 `a8c0e2f4b6d8`）：物品名称、数量、关联设备（验收时必填）、申请人、状态、备注；`GET/POST /api/procurements` 与 `PUT /api/procurements/{id}`、`DELETE /api/procurements/{id}`（管理员）。
  - 状态机：`pending 申请中 → arrived 已到货 → accepted 已验收`，只允许前进一步——跳级/回退/重复验收都返回 400，验收时 `equipment.quantity += quantity` 只执行一次；已验收记录不允许删除（保留审计轨迹），pending/arrived 可删。
  - 前端：新增「采购管理」页（管理员菜单）：状态/名称筛选、录入弹窗（可选关联设备）、行内「标记到货 / 验收入库 / 删除」，toast 与确认框齐备。
  - 配套：回归测试 `test_procurement_flow_updates_stock_once` 覆盖跳级拒绝、到货、验收入库 +3、重复验收拒绝、已验收不可删、普通用户 403、pending 可删，26 个测试全部通过。
- [x] **11. 实验课程模块 + 课表冲突校验** ✅ 2026-10-21 已完成
  - 参考：zongjixiaoai66 实验课程、marspal-ai 课表冲突
  - 后端：新增 `courses` / `course_enrollments` 表（Alembic 迁移 `b1d3f5a7c9e2`）：课程名称、实验室、授课教师、周几（1-7）、上课时间段、学期区间、说明；选课名单唯一约束防重复。
  - 冲突校验（双向统一）：
    - 预约侧：`services/reservation.py` 的 `check_slot_available` 新增课表检查——预约日期落在课程学期内、周几匹配、时间段重叠即拒绝（`课程《xxx》占用`），创建与修改预约共用；
    - 课程侧：`services/course.py` 的 `find_course_conflict` 判同实验室课表重叠；`api/course.py` 再查学期区间内的既有预约（按周几在应用层过滤，规避数据库间 weekday 函数差异），建课/改课都用「更新后最终值」重新校验，防止部分更新绕过。
  - 权限：教师/管理员建课、删课（只能管理自己的课，管理员例外），学生只读；`GET /api/courses`（lab/关键词/我的课程过滤）、`GET /api/courses/available-students`、选课名单增删接口。
  - 前端：新增「实验课程」页：课程表（星期/时间/学期/选课人数）、建课/编辑弹窗（时间区间 + 学期区间）、选课名单弹窗（多选学生加入、行内移出），学生端只读且可勾选「我的课程」。
  - 配套：回归测试 `test_course_schedule_blocks_overlapping_reservations` 覆盖课程→预约冲突、相邻时段放行、课程间冲突、预约→课程冲突、名单幂等增删、学生 403、我的课程过滤，27 个测试全部通过。
- [x] **12. 多维数据导出** ✅ 2026-10-21 已完成
  - 现状：仅预约可导出
  - 后端：新增 `services/export.py` 的 `build_excel_response`（openpyxl 统一封装：表头 + 数据行 → xlsx 下载响应，文件名走 RFC 5987 `filename*=UTF-8''` 编码防中文乱码），补三个导出接口（均管理员且与列表筛选一致）：`GET /api/equipment/export`（设备编号/名称/实验室/数量/状态/说明/操作说明/创建时间）、`GET /api/repairs/export`（报修人/实验室/设备/标题/描述/状态/处理人/备注/时间）、`GET /api/user/export`（用户名/姓名/邮箱/角色/状态/创建时间）。
  - 修复：报修导出路由必须声明在 `GET /api/repairs/{repair_id}` 之前，否则 `/{repair_id}` 会把 "export" 当 ID 解析（FastAPI 路由按声明顺序匹配），测试立刻暴露了这一点。
  - 前端：`utils/request.js` 对 `responseType: 'blob'` 放行原始响应（不套统一信封），新增 `utils/download.js` 解析 Content-Disposition 触发下载；设备/报修/用户三个页面按权限加「导出」按钮。
  - 配套：回归测试 `test_multi_entity_excel_exports` 用 openpyxl 读回 xlsx 校验表头与行内容，并验证普通用户导出 403；28 个测试全部通过。
- [x] **13. 邮件通知** ✅ 2026-10-21 已完成
  - 后端：新增 `services/email.py`（标准库 smtplib + EmailMessage，**不引入 aiosmtplib**——省一个依赖且无需异步改造）：`build_notification_email` 纯函数组装邮件、`send_notification_email` 发送；未配置 `SMTP_HOST`/`SMTP_FROM` 时直接返回 False（零网络副作用），发送失败只记 warning、绝不抛给业务。
  - 接入三处业务：预约审核通过/驳回（`api/reservation.py`，`BackgroundTasks` 异步发信，不拖慢接口）、报修处理结果（`api/repair.py`）、开课前提醒（`services/schedule.py` 的 `remind_upcoming_reservations`，调度线程内同步发信、10 秒超时）。
  - 配置：`config.py` 新增 `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM/USE_TLS`，`.env.example` 补说明（QQ/163 用授权码）；未配置时降级为仅站内通知。
  - 配套：回归测试 `test_email_notifications_wire_and_skip` 覆盖邮件头/正文纯函数、未配置静默跳过（不连网）、审核/提醒/报修三处 wiring（mock 断言收件人与主题），29 个测试全部通过；本项纯后端通道，无前端改动。

### P2 —— 进阶 / 锦上添花

- [ ] **14. 工位级预约 + 图形化选室**（marspal-ai）：评估结论：暂缓（结论见下方）
  - 未做原因：需要实验室平面图与工位坐标数据，仓库与当前环境都没有真实素材；凭空造图做出的选座没有使用价值。
  - 落地条件：院系提供实验室平面图（或 CAD/图片）+ 工位编号与坐标。
  - 实施要点：新增 `seats` 表（lab_id、编号、x/y、状态）与预约↔工位绑定；前端 canvas/SVG 绘制热区，点选后带入预约表单；冲突校验沿用现有时间段逻辑 + 工位维度。
- [ ] **15. 安全准入考试**（marspal-ai）：评估结论：暂缓
  - 未做原因：题库属于院系教学资产（安全规范考题），无法凭空生成；假题库会让「准入」形同虚设。
  - 落地条件：提供题库（题目/选项/答案/及格线）与适用范围（按实验室或按设备）。
  - 实施要点：`questions` / `exams` / `exam_answers` 表；`users` 增加 `lab_qualified_at` 或独立资格表；预约创建时校验资格，未通过跳转考试页；考试成绩与操作日志留痕。
- [ ] **16. 二维码签到/核销**（ICRS/marspal-ai）：评估结论：暂缓
  - 未做原因：核销动作发生在移动端（扫码），当前只有 PC Web；没有移动端/小程序时功能闭环不了（生成二维码容易，能扫码签到才是关键）。
  - 落地条件：小程序或移动 H5 上线后接入。
  - 实施要点：预约通过后生成带签名的一次性 token（QR 内容），扫码端调 `POST /api/reservations/{id}/checkin` 校验 token/时效/实验室；过期未签到由定时任务标记 `no_show`（爽约）并影响后续预约配额。
- [ ] **17. RBAC 动态菜单权限**（vue-fastapi-admin）：评估结论：暂缓（原计划即有「想做成通用平台再上」的取舍）
  - 未做原因：当前三角色（学生/教师/管理员）硬编码已覆盖全部业务权限，动态 RBAC 是通用平台能力，引入后反而增加使用与维护成本。
  - 落地条件：出现多租户、自定义角色或按学院分权的真实需求。
  - 实施要点：role / menu / permission 三表 + 前端动态菜单渲染 + 后端依赖注入权限码；迁移期保留现有 `is_superuser/is_teacher` 兼容。
- [x] **18. Refresh Token 无感刷新** ✅ 2026-10-21 已完成
  - 后端：`utils/jwt.py` 增加 `create_refresh_token`（type=refresh，有效期 `JWT_REFRESH_EXPIRE_DAYS`，默认 7 天）；两个令牌都带 `type` 与随机 `jti`（同秒多次签发不再产生相同字符串）。`dependencies/auth.py` 只接受 `type=access`，刷新令牌不能当访问凭证用；登录响应新增 `refresh_token` 字段。
  - 新接口：`POST /api/auth/refresh`——校验链「签名/过期 → type=refresh → 用户存在且启用 → 密码版本一致」，通过后返回新 access + 轮换后的 refresh；改密后旧 refresh 与旧 access 一起失效（复用 password_version 指纹，不落库，零表结构变更）。
  - 前端：`utils/auth.js` 独立管理 refresh token（登出一起清除）；`utils/request.js` 在 HTTP 401 时用裸 axios 单飞调用刷新接口（`refreshPromise` 去重，避免并发递归），拿到新 token 后重放原请求；刷新失败才登出跳转登录页。
  - 已知取舍：refresh token 不落库，无法单独吊销某台设备（依赖改密全量失效）；多设备精细吊销需要 refresh_token 表。
  - 配套：回归测试 `test_refresh_token_flow_and_invalidation` 覆盖登录下发、换新令牌、双向类型隔离、改密后旧 refresh 失效，30 个测试全部通过（本项与 P2-18/32 合并实施）。
- [x] **19. 接口限流** ✅ 2026-10-21 已完成
  - 后端：新增 `middleware/rate_limit.py`（内存固定窗口计数，线程安全）：认证接口（登录/注册/刷新）10 次/分钟、AI 接口 30 次/分钟、其余 `/api` 120 次/分钟，超限返回 429 + `Retry-After`；探活/指标/静态资源跳过。限流注册在审计中间件外层——被限流的请求不产生审计日志噪音。
  - 配置：`RATE_LIMIT_ENABLED` / `RATE_LIMIT_AUTH_PER_MINUTE` / `RATE_LIMIT_AI_PER_MINUTE` / `RATE_LIMIT_PER_MINUTE`；测试环境默认关闭，专门用例临时开启。
  - 已知取舍：内存实现，重启清零、多 worker 各自计数（阈值实际放大），需要精确限流时换 Redis。
- [x] **20. 启用 Sentry 错误监控** ✅ 2026-10-21 已完成
  - `services/observability.py` 的 `init_sentry()`：`SENTRY_DSN` 为空直接跳过（零上报尝试），配置后初始化 SDK 并设置 `environment` / `traces_sample_rate`；初始化失败只记 warning 不拖垮启动。`main.py` 应用创建后调用，`sentry-sdk` 惰性导入。
- [ ] **21. 微信小程序端**：评估结论：暂缓
  - 未做原因：需要微信开发者账号、小程序 AppID、已备案的服务端域名与审核发布流程，当前环境无法验证真机效果。
  - 落地条件：具备微信小程序主体与备案域名。
  - 实施要点：直接复用现有 REST API；小程序 `wx.login` code 换 openid 后调用登录接口映射本地账号；通知走订阅消息（事件与现有站内通知同源）；图片走 `wx.uploadFile` 复用上传接口。

## 四、建议节奏

1. **第一周**：P0-1 日历视图 + P0-2 图表（纯前端为主，见效快）
2. **第二周**：P0-3 定时任务 + P0-5 登录安全（后端独立，互不阻塞）
3. **第三周**：P0-4 WebSocket 通知 + P0-6 操作日志
4. **之后**：按 P1 顺序推进，P2 视项目定位取舍（毕设/作品集可优先 14/15/16 增加亮点）

> 提交建议：每完成一项勾选对应复选框，并在 README「已实现功能」同步登记。

## 五、企业级应用差距对比

> 本节把对比基准从"同类开源项目"升级为**企业级标准**，新增待办项编号接前文（22 起）。
> 三类参照物：
> 1. **商业 LIMS 产品**：[LabWare LIMS](https://www.labware.com/lims)（ELN、Mobile、系统集成、SaaS 多租户、Testing & Validation 合规验证）、STARLIMS、LabVantage、三维天地 SW-LIMS；
> 2. **生产级工程实践**：[zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)（18k★，任务队列、Refresh Token、结构化日志、Sentry）、Netflix [Dispatch](https://github.com/Netflix/dispatch) 的项目结构、12-Factor 配置治理；
> 3. **国内合规要求**：《网络安全法》第 21 条（网络日志留存不少于 6 个月）、等保 2.0（身份鉴别、审计留存、数据备份恢复）。

### 差距总览

| 维度 | 当前状态（已核实） | 企业级标准 | 差距 |
| --- | --- | --- | --- |
| 身份认证 | 本地账密 + JWT，无刷新机制 | SSO（高校统一身份认证 CAS/OIDC/LDAP）、MFA、Refresh Token | ★★★ |
| 审计合规 | 无操作日志（P0-6 待做）；无日志留存策略 | 全量操作审计、日志留存 ≥6 个月、敏感操作电子签名 | ★★★ |
| 工程效能 | **无 CI**（无 `.github/`），测试靠本地手动跑 | CI 流水线（lint + test + build + 镜像扫描）、覆盖率门禁、多环境分离 | ★★★ |
| 可观测性 | 仅 AI 模块 logger + 全局异常捕获；无 access log / request_id / 指标 | 结构化日志 + 链路追踪、Prometheus 指标、Grafana 看板、Sentry 告警 | ★★★ |
| 可用性 | docker compose 单实例 | 多副本 + 负载均衡、readiness 探针分流、优雅停机、滚动升级 | ★★ |
| 数据保护 | DEPLOY.md 有**手动**备份命令（mysqldump + uploads 打包） | 每日自动备份 + 异地存储 + 定期恢复演练（RTO/RPO 指标） | ★★ |
| 任务与消息 | 线程 + 30 秒轮询；无任务队列 | Celery/RQ + 消息队列：重试、死信、任务监控（best-practices 明确建议） | ★★ |
| 性能扩展 | 本地 uploads 目录、无缓存、单库 | Redis 缓存、对象存储（S3/MinIO）、CDN、读写分离 | ★★ |
| API 治理 | `/api/*` 无版本号；统一响应已有 | `/api/v1` 版本化、废弃策略、破坏性变更流程 | ★ |
| 产品深度 | 预约/设备/报修的事务管理 | ELN 电子实验记录、样品全生命周期、仪器数据集成、报表中心、审批流引擎 | ★★★（按定位取舍） |

### 待办项

#### E1 工程效能（差距最大、成本最低，最先做）

- [x] **22. CI/CD 流水线（GitHub Actions）** ✅ 2026-10-21 已完成
  - 新增 `.github/workflows/ci.yml`，三个 job：①后端（pip 安装 requirements-all → `ruff check` → `ruff format --check` → SQLite 回归测试，CI 缺失的 `JWT_SECRET_KEY` 从 job env 注入）；②前端（Node 22 + `npm ci` + `npm run build`，带依赖缓存）；③镜像构建（backend/frontend 两个 Dockerfile 都构建），`needs` 串起前后端、任一失败即整体失败。
- [x] **23. 代码质量门禁** ✅ 2026-10-21 已完成
  - 新增 `backend/pyproject.toml`（ruff：line-length 120、select E4/E7/E9/F/I/W、忽略 E501；tests 目录放行 F401/E402——`test_api.py` 必须先设环境变量再导入 app，E402 是刻意为之）。
  - 全仓 `ruff check` 0 error；一次性执行 `ruff format`（46 个文件重排），format --check 已全绿；31 个测试在格式化后全部通过。
  - mypy 渐进式未实施：项目无类型注解基线，先由 ruff 把语法/未定义名问题卡住，mypy 留作后续在核心模块试点。
- [x] **24. 多环境分离** ✅ 2026-10-21 已完成
  - 新增 `backend/.env.staging.example` 与 `backend/.env.production.example`（预发/生产的差异项：`AUTO_CREATE_TABLES=false`、Sentry 环境与采样率、限流阈值、验证码锁定 30 分钟、SMTP 465 隐式 TLS 等）；`DEPLOY.md` 增加「多环境分离」章节：密钥注入、迁移顺序、调度器单实例、可观测性接入与回滚约定。

#### E2 可观测性

- [x] **25. 结构化日志与链路追踪** ✅ 2026-10-21 已完成
  - 新增 `common/context.py`（ContextVar 保存 request_id）+ `middleware/request_id.py`（生成/透传 `X-Request-ID` 并回写响应头、`RequestIdFilter` 把 ID 注入每条日志、`configure_logging()` 统一格式 `时间 级别 [request_id] 模块: 消息`）；`main.py` 启动即配置，`LOG_LEVEL` 可调。
  - 效果：同一次请求的日志可按 request_id 串起来，前端/网关报错时带上响应头里的 ID 即可定位；后续接入日志平台（Loki/ELK）可直接解析该格式。
- [x] **26. 指标监控（Prometheus + Grafana）** ✅ 2026-10-21 已完成
  - 引入 `prometheus-fastapi-instrumentator`（`requirements.txt`/`requirements-all.txt` 已登记），`services/observability.py` 的 `setup_metrics()` 暴露 `/metrics`：QPS、延迟分位、状态码分布等默认指标；`METRICS_ENABLED` 可关闭，指标初始化失败只记 warning。
  - 说明：Grafana 看板不在仓库内（需外部 Grafana 实例），指标已就绪可直接接。
- [x] **27. `/health` 升级为 readiness 检查** ✅ 2026-10-21 已完成
  - `/health` 保留为存活探针；新增 `/ready`：`SELECT 1` 探测数据库可达，正常 200 `{"status":"ready","database":"ok"}`，异常 503（不抛异常栈）；`docker-compose.yml` 后端 healthcheck 改打 `/ready`。
  - 说明：ChromaDB 可达性未纳入探针——它是 AI 检索的可选依赖，不应拖垮主服务就绪状态。

#### E3 数据安全与合规

- [x] **28. 数据库自动备份 + 恢复演练** ✅ 2026-10-21 已完成
  - 新增 `scripts/backup.sh`：`mysqldump --single-transaction` 全量导出 + uploads 数据卷打包，默认保留 30 天（`RETENTION_DAYS` 可调），支持宿主机 crontab 每日执行。
  - `DEPLOY.md` 增加「自动备份与恢复演练」章节：cron 示例、季度恢复演练步骤（导入备份→启动→抽查登录/图片/统计一致性）、RTO/RPO 指标建议与异地存放要求。
- [x] **29. 日志留存与审计合规** ✅ 2026-10-21 已完成（2026-10-28 补充 AI 工具审计）
  - 留存策略：`services/audit.py` 的 `purge_expired_audit_logs` 按 `AUDIT_RETENTION_DAYS`（默认 180 天）清理登录/操作日志，2026-10-28 起把 `agent_tool_logs`（AI 写工具审计/幂等记录）纳入同一留存期；APScheduler 每天 03:00 执行。登录日志已记录 IP/UA（P0-5），操作日志记录操作人/角色/路径/结果/IP/耗时（P0-6）。
  - 审计报告：`GET /api/operation-logs/export`（按操作人+时间范围导出操作审计）与 `GET /api/auth/login-logs/export`（登录审计），均管理员专属、复用通用 Excel 封装；前端操作日志页新增时间范围筛选 +「导出审计报告」。
  - 配套：回归测试覆盖过期记录被清理、保留期内记录保留、两类审计导出可用且普通用户 403。
- [x] **30. 敏感操作电子签名（LIMS 合规向）** ✅ 2026-10-21 已完成
  - `dependencies/signature.py`：`require_signature` 依赖（查询参数 `signature_password`）与 `verify_signature` 函数，二次确认当前账号密码；开关 `SIGNATURE_REQUIRED`（默认开，测试环境关闭）。
  - 二次验证有效期：`SIGNATURE_TTL_MINUTES`（默认 5 分钟）——验证通过后窗口内重复危险操作免输（类似 sudo），按用户+密码指纹缓存，改密/超时/重启自动失效；设为 0 退化为每次都要输入。
  - 覆盖范围：删除实验室/设备/用户/公告（依赖注入）+ 预约审核驳回（端点内校验）；校验通过后操作日志自动记录「谁、何时、做了什么、结果」，即电子签名证据链。
  - 前端：删除按钮改为 `ElMessageBox.prompt` 密码确认（`utils/confirm.js`）；预约审核弹窗在「拒绝」时显示二次验证密码输入框与有效期提示（5 分钟内已验证可留空）。
  - 配套：回归测试验证缺失密码 400、错误密码 400、正确密码成功，以及 TTL 窗口内免密/清缓存后重新要求的完整流程。
- [x] **31. 上传文件安全治理** ✅ 2026-10-21 已完成
  - 现状复核：上传接口已具备「MIME 白名单 + 文件头/尾内容校验 + 5MB 限制 + UUID 文件名」（P0 阶段遗留测试覆盖），本次补扫描钩子。
  - 新增 `services/antivirus.py`：`CLAMAV_COMMAND` 配置后对落盘文件执行扫描（退出码 0 干净 / 1 感染），`CLAMAV_REQUIRED=true` 时扫描器异常也拒绝；感染文件立即删除并返回 400「文件未通过安全扫描」；未配置时放行并返回 `scan: skipped`。
  - 说明：下载未改为鉴权代理——前端图片以 `<img src="/uploads/...">` 直接展示，改为需要 Header 的鉴权接口会破坏所有图片；后续接入附件（PDF 等）时可用带签名或带 token 的下载接口，已在 TODO 记录该取舍。

#### E4 认证与架构升级

- [x] **32. Refresh Token + 无感刷新** ✅ 2026-10-21 已完成（与 P2-18 合并实施，实现细节见第 18 项）
  - 参考：fastapi-best-practices 的 auth 配置分层（JWT_EXP + REFRESH_TOKEN_EXP）
  - 结论：短效 access（`JWT_EXPIRE_HOURS`）+ 长效 refresh（`JWT_REFRESH_EXPIRE_DAYS`）已落地；「可吊销」当前仅通过改密触发全量失效（password_version 指纹），做到按设备独立吊销还需新增 refresh_token 表（随 P2 需要再上）。
- [ ] **33. 统一身份认证（SSO）对接**：评估结论：暂缓
  - 未做原因：需要学校统一身份认证的测试端点与账号（CAS/OIDC/LDAP），当前环境无法联调。
  - 落地条件：校方提供 IdP 配置（endpoint/client_id/secret/证书）。
  - 实施要点：auth 增加 `/sso/login` 分支，回调后按学号/工号映射本地 `users`（首次自动建号并标 `is_active`），保留本地账密登录兜底与管理员紧急入口。
- [ ] **34. 任务队列（Celery + Redis）**：评估结论：暂缓
  - 未做原因：需要 Redis 服务与额外的队列运维（worker/beat/监控），当前单机环境引入后可靠性收益有限。
  - 落地条件：部署 Redis（或云 Redis），出现导出/群发/长任务并发压力。
  - 实施要点：Celery + Redis broker；把 Excel 导出、通知群发、邮件发送迁入任务，带重试与死信告警；APScheduler 的定时任务并入 Celery beat（多副本只跑一个 beat）。
- [ ] **35. 对象存储 + 水平扩展准备**：评估结论：暂缓
  - 未做原因：需要 MinIO/S3 或云对象存储凭据；当前 uploads 本地卷 + Nginx 直出在单机部署下工作正常。
  - 落地条件：提供对象存储实例（MinIO/S3/OSS）与访问密钥。
  - 实施要点：上传改预签名 URL 直传（服务端只签发与校验），下载走短时效签名 URL；历史 uploads 迁移 + 旧路径兼容；应用容器无状态后可多副本部署，配合 Redis 缓存热点查询。

#### E5 产品深度（LIMS 深水区，按项目定位取舍）

- [x] **36. 审批流引擎** ✅ 2026-10-28 已完成
  - 数据模型：新增 `approval_flows` / `approval_steps` / `reservation_approvals` 三表（Alembic 迁移 `c9e1f3a5b7d2`），`reservations` 增加 `approval_flow_id` 与 `approval_step_order`；预约创建时快照适用的流程与首节点，后续改流程名称/停用不影响已提交的预约。
  - 节点能力：每个实验室一条流程，支持 1–8 个节点；节点可按角色（全部管理员 / 全部教师）或指定人员审批，并填写节点名称（如「导师初审」）。有预约引用过的流程不允许再改节点，只允许改名/说明/停用，保证历史轨迹可解释；未使用的流程可删除。
  - 流转规则：首节点通过后预约仍为 pending 并推进到下一节点，全部节点通过才置为 approved；任一节点拒绝即 rejected 并结束；最终通过前复核预约时间与实验室开放状态。管理员保留兜底处理权限，但不能审批自己的预约。
  - 通知与审计：进入每个节点后给该节点审批人发送站内通知并 WebSocket 实时推送；最终结果/驳回沿用邮件通知；每次通过/拒绝写入 `reservation_approvals`（节点名称快照、审批人、意见、时间），申请人可在「审批进度」中查看时间线。
  - 改约重走：学生修改待审核预约且已有审批记录时，旧轨迹作废、节点回到第 1 步并重新通知首节点审批人，避免用旧审批覆盖新时间/用途。
  - 兼容：未配置流程的实验室保持原来的单级审核；预约列表新增 `pending_for_me` 过滤与 `approval` 摘要，导出 Excel 增加「审批流/节点」两列。
  - 前端：新增管理员「审批流配置」页（节点增删、角色/指定人员、启用停用、删除保护）；预约页增加审批进度列、进度时间线弹窗、按节点显示通过/拒绝按钮、「只看待我审批」筛选。
  - 配套：回归测试 `test_approval_flow_multi_step_and_reset_on_edit` 覆盖两级流转、非当前节点 403、节点通知、驳回、终审、改约重走、流程删除/改节点保护、停用后新预约回到单级审核；后端测试增至 40 个。
- [x] **37. 报表中心** ✅ 2026-10-21 已完成
  - 后端：新增 `api/report.py`：`GET /api/reports/usage`（默认最近 30 天，可传 start_date/end_date/lab_id）返回三段数据——totals（预约数/已通过/机时/使用人数/课程机时/预估费用）、by_lab（按实验室）、by_user（按用户）；机时只统计 approved，课程机时按课表在区间内的实际发生次数折算；费用 = 机时 × `LAB_HOUR_RATE`（.env 可配，0 表示不计算）。
  - 导出：`GET /api/reports/usage/export` 双工作表（按实验室 / 按用户），通用导出封装新增 `extra_sheets` 参数。
  - 前端：新增「报表中心」页（管理员菜单）：日期范围 + 实验室筛选、四张汇总卡、两张明细表、导出按钮。
  - 配套：回归测试 `test_usage_report_and_export` 校验统计口径（2 条已通过预约 ≈ 2 机时、费用按单价）、双工作表导出、普通用户 403，33 个测试全部通过。
- [ ] **38. 样品/耗材全生命周期**：评估结论：暂缓
  - 未做原因：属于商业 LIMS 的深水区（样品登记、流转、处置、耗材出入库与库存预警），数据模型与流程复杂，需要真实的样品管理口径。
  - 落地条件：明确样品/耗材管理需求（编号规则、流转环节、预警阈值）。
  - 实施要点：`samples` + `sample_events` 表（状态机），耗材入库/出库记录与现有采购模块联动（验收入库 → 耗材库存），低库存定时提醒。
- [ ] **39. 仪器数据集成**：评估结论：暂缓
  - 未做原因：依赖具体仪器/厂商接口（Modbus、串口、LIMS 网关、摄像头 SDK），当前环境没有可连接的硬件，无法验证。
  - 落地条件：提供仪器接口文档或上机时长/状态数据源。
  - 实施要点：设备心跳与工时采集入库（`equipment_telemetry`），与预约记录关联做上机时长校对与计费；图片类设备（摄像头人数）走定时采集 + 报表展示。

### 实施建议

- E1（22–24）建议**立即做**：一次配置长期受益，且是后续所有工程项的地基；
- E2、E3 在完成 P0-6（操作日志）后跟进，共用表结构与中间件；
- E4 是"换引擎"级别的重构，建议在功能线（P1）稳定后启动；
- E5 视项目定位：**毕设/作品集**选 36–37 即可显著提升含金量；**真实落地高校**才考虑 38–39。

