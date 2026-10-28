# 接口性能测试（本地开发环境）

> 测试时间：2026-10-28  
> 目的：给答辩/面试一个可复现的数量级参考，不是生产容量承诺。

## 1. 环境与数据

| 项目 | 配置 |
| --- | --- |
| 机器 | Windows 11，i7-12650H（10 核 16 线程） |
| Python | 3.14.6 |
| 服务 | `uvicorn app.main:app --port 8002`，**单 worker**，无 `--reload` |
| 数据库 | 本地 MySQL 8.4 |
| 调度器 | `SCHEDULER_ENABLED=false`（避免定时任务干扰） |
| 限流 | `RATE_LIMIT_ENABLED=false`（压测期间关闭） |
| 数据量 | 25 用户、17 实验室、24 设备、203 条预约（60 已通过、40 待审核） |

被测接口（全部 GET、只读）：

- `/api/labs?only_open=true`
- `/api/reservations?status=approved`
- `/api/stats/dashboard?days=30`
- `/api/reports/usage`
- `/api/announcements`
- `/api/notifications/unread-count`
- `/api/courses`

## 2. 方法

脚本：`backend/scripts/bench_api.py`。

- 先登录拿 JWT，再按接口轮询发请求；
- 预热 20 次，不计入结果；
- 固定总请求数，分别测并发 1 / 10 / 20；
- 统计成功数、QPS、均值、P50/P95/P99；
- 只打 GET，不写业务数据；失败只记录，不中断。

复现命令：

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\bench_api.py --base-url http://127.0.0.1:8002 `
  --username e2e_admin --password E2eAdmin123! --requests 300 --concurrency 10
```

## 3. 结果

### 3.1 总览

| 并发 | 总请求 | 成功 | QPS | 均值 | P50 | P95 | P99 | 最大 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 120 | 120/120 | 64.89 | 15.38 ms | 17.01 ms | 26.26 ms | 26.90 ms | 28.57 ms |
| 10 | 300 | 300/300 | 87.19 | 113.68 ms | 105.88 ms | 186.20 ms | 238.22 ms | 242.35 ms |
| 20 | 300 | 300/300 | 105.94 | 184.68 ms | 175.87 ms | 261.97 ms | 310.56 ms | 345.28 ms |

### 3.2 并发 10 的分接口数据

| 接口 | 样本 | 均值 | P95 |
| --- | --- | --- | --- |
| `/api/labs?only_open=true` | 43 | 97.53 ms | 148.11 ms |
| `/api/reservations?status=approved` | 43 | 143.49 ms | 231.33 ms |
| `/api/stats/dashboard?days=30` | 43 | 101.53 ms | 136.96 ms |
| `/api/reports/usage` | 43 | 156.99 ms | 217.76 ms |
| `/api/announcements` | 43 | 99.44 ms | 145.27 ms |
| `/api/notifications/unread-count` | 43 | 89.64 ms | 122.07 ms |
| `/api/courses` | 42 | 107.00 ms | 153.99 ms |

## 4. 解读

- **串行**（并发 1）平均 15 ms、P95 26 ms，说明单请求本身不慢；主要成本在数据库查询 + JSON 序列化 + JWT 校验。
- **并发 10** 时 QPS 约 87、P95 约 186 ms；**并发 20** 时 QPS 约 106、P95 约 262 ms。
- 单 worker 下 QPS 在 100 左右趋于平台，延迟随并发上升；继续加压会先看到尾延迟恶化，而不是线性扩容。
- 最重的两个接口是 `/api/reservations` 和 `/api/reports/usage`：前者带用户/实验室/审批关联预加载，后者做多段聚合。优化方向是索引、聚合缓存/预计算、只取必要字段。
- 该结果**不能**直接外推为生产容量：单进程、Windows、开发机、数据量小、未压测写接口。生产应使用多 worker/多副本 + 负载均衡，并用真实数据量重测。

## 5. 已知边界

- 限流、登录锁定、WebSocket 连接管理都是单进程内存实现；多 worker 下阈值/推送行为会变化。
- 写接口（创建预约、审核、导出）未纳入本次压测；导出 Excel 是 CPU/内存密集型，应单独测。
- AI 对话涉及外部模型/SSE，未纳入本表；它的瓶颈在上游模型和首 token 延迟，而不是 FastAPI 读接口。