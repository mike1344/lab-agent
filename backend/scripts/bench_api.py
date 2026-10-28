"""对本地运行中的 lab_agent 做只读接口压测，输出 QPS / P50 / P95 / P99。

前提：
- 后端已启动，且测试账号可登录（压测环境建议 LOGIN_CAPTCHA_ENABLED=false、RATE_LIMIT_ENABLED=false）；
- 只打 GET 接口，不写业务数据；
- 结果是开发机单进程 uvicorn 的参考值，不是生产容量承诺。

用法（backend 目录）：
    .\\.venv\\Scripts\\python.exe scripts\\bench_api.py --base-url http://127.0.0.1:8002 \
        --username e2e_admin --password E2eAdmin123! --requests 300 --concurrency 10
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx

ENDPOINTS = [
    "/api/labs?only_open=true",
    "/api/reservations?status=approved",
    "/api/stats/dashboard?days=30",
    "/api/reports/usage",
    "/api/announcements",
    "/api/notifications/unread-count",
    "/api/courses",
]


@dataclass
class Sample:
    endpoint: str
    status: int
    latency_ms: float
    error: str = ""


def login(client: httpx.Client, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    payload = response.json()
    if response.status_code != 200 or payload.get("code") != 200:
        raise SystemExit(f"登录失败：HTTP {response.status_code}，{payload.get('message') or payload}")
    return payload["data"]["token"]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * ratio))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="lab_agent 只读接口压测")
    parser.add_argument("--base-url", default="http://127.0.0.1:8002")
    parser.add_argument("--username", default="e2e_admin")
    parser.add_argument("--password", default="E2eAdmin123!")
    parser.add_argument("--requests", type=int, default=300)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=20)
    args = parser.parse_args()

    limits = httpx.Limits(max_connections=args.concurrency * 2, max_keepalive_connections=args.concurrency)
    with httpx.Client(base_url=args.base_url, timeout=30, limits=limits) as client:
        token = login(client, args.username, args.password)
        headers = {"Authorization": f"Bearer {token}"}
        print(f"登录成功：{args.username}")
        print(f"目标：{args.base_url}，并发 {args.concurrency}，总请求 {args.requests}")
        print("接口：" + "、".join(ENDPOINTS))
        print("-" * 72)

        def one(index: int) -> Sample:
            endpoint = ENDPOINTS[index % len(ENDPOINTS)]
            started = time.perf_counter()
            try:
                response = client.get(endpoint, headers=headers)
                latency = (time.perf_counter() - started) * 1000
                error = "" if response.status_code == 200 else f"HTTP {response.status_code}"
                return Sample(endpoint, response.status_code, latency, error)
            except Exception as exc:  # noqa: BLE001 - 压测脚本需要记录失败而不是中断
                return Sample(endpoint, 0, (time.perf_counter() - started) * 1000, type(exc).__name__)

        # 预热连接池、JWT 依赖与查询缓存，避免把冷启动算进结果
        for index in range(max(0, args.warmup)):
            one(index)

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            samples = list(pool.map(one, range(args.requests)))
        elapsed = time.perf_counter() - started

    latencies = [sample.latency_ms for sample in samples if not sample.error]
    errors = [sample for sample in samples if sample.error]
    print(f"总耗时：{elapsed:.2f}s")
    print(f"QPS：{len(samples) / elapsed:.2f}")
    print(f"成功：{len(latencies)} / {len(samples)}，失败：{len(errors)}")
    if latencies:
        print(
            f"延迟(ms)：均值 {statistics.mean(latencies):.2f}，"
            f"P50 {percentile(latencies, 0.50):.2f}，"
            f"P95 {percentile(latencies, 0.95):.2f}，"
            f"P99 {percentile(latencies, 0.99):.2f}，"
            f"最大 {max(latencies):.2f}"
        )

    print("-" * 72)
    print("按接口统计：")
    for endpoint in ENDPOINTS:
        group = [sample.latency_ms for sample in samples if sample.endpoint == endpoint and not sample.error]
        group_errors = [sample for sample in errors if sample.endpoint == endpoint]
        if group:
            print(
                f"{endpoint:38s} n={len(group):3d} "
                f"mean={statistics.mean(group):7.2f}ms p95={percentile(group, 0.95):7.2f}ms "
                f"err={len(group_errors)}"
            )
        else:
            print(f"{endpoint:38s} n=0 err={len(group_errors)}")

    if errors:
        print("失败样例：")
        for sample in errors[:5]:
            print(f" - {sample.endpoint} {sample.status} {sample.error}")


if __name__ == "__main__":
    main()
