"""可观测性：Sentry 错误上报 + Prometheus 指标。

两者都遵循「配置了才启用」的降级风格：
- SENTRY_DSN 为空 → 跳过初始化，不产生任何上报尝试；
- METRICS_ENABLED=false → 不挂载 /metrics。
依赖均为惰性导入，未启用时不会因为缺包而启动失败。
"""

import logging

from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger("lab_agent")


def sentry_configured() -> bool:
    return bool(settings.SENTRY_DSN)


def init_sentry() -> bool:
    """初始化 Sentry；未配置或初始化失败返回 False，不影响应用启动。"""
    if not sentry_configured():
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        )
        logger.info("Sentry 已启用（environment=%s）", settings.SENTRY_ENVIRONMENT)
        return True
    except Exception:  # noqa: BLE001 - 监控初始化失败不能拖垮主服务
        logger.warning("Sentry 初始化失败，已跳过错误上报")
        return False


def setup_metrics(app: FastAPI) -> bool:
    """挂载 Prometheus /metrics（QPS、延迟分位、状态码分布等默认指标）。"""
    if not settings.METRICS_ENABLED:
        return False
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("Prometheus 指标已挂载：/metrics")
        return True
    except Exception:  # noqa: BLE001 - 指标不可用不应影响业务
        logger.warning("Prometheus 初始化失败，已跳过指标暴露")
        return False
