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
    # 刷新令牌有效期（天）：过期后必须重新登录
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    # 允许跨域的前端来源，多个用英文逗号分隔；部署时改成真实前端域名
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    # 开发便捷：启动时自动创建缺失的表；生产环境建议关闭，改由 Alembic 迁移管理表结构
    AUTO_CREATE_TABLES: bool = True
    # 定时任务（过期预约自动关闭、开课前提醒）。多副本部署时只应在一个实例上开启，
    # 避免重复发通知；单机部署保持默认开启即可。
    SCHEDULER_ENABLED: bool = True
    # 登录安全：图形验证码开关、失败锁定策略与验证码有效期。
    # 失败计数为内存实现，进程重启即清零；多 worker 部署时各进程独立计数。
    LOGIN_CAPTCHA_ENABLED: bool = True
    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    CAPTCHA_EXPIRE_MINUTES: int = 5
    # 邮件通知（可选）：不配置 SMTP_HOST / SMTP_FROM 时静默跳过，功能降级为仅站内通知。
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True
    # 可观测性与限流
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_AI_PER_MINUTE: int = 30
    METRICS_ENABLED: bool = True
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    # 审计留存（《网络安全法》第 21 条要求不少于 6 个月）与危险操作二次确认
    AUDIT_RETENTION_DAYS: int = 180
    SIGNATURE_REQUIRED: bool = True
    # 二次验证有效期（分钟）：验证通过后该窗口内重复危险操作无需再输入；0 = 每次都要
    SIGNATURE_TTL_MINUTES: int = 5
    # 上传文件病毒扫描（可选）：配置后对每个上传文件执行扫描命令
    CLAMAV_COMMAND: str = ""
    CLAMAV_REQUIRED: bool = False
    # 报表中心：机时单价（元/小时），0 表示只统计机时不算费用
    LAB_HOUR_RATE: float = 20.0
    # RAG 检索：local（离线哈希向量）| bge（sentence-transformers）| api（OpenAI 兼容 Embedding）
    RAG_PROVIDER: str = "local"
    RAG_EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    RAG_TOP_K: int = 4
    # 混合权重：向量占比，其余给 BM25
    RAG_HYBRID_ALPHA: float = 0.6
    # 最低置信度：低于该分数的证据会被丢弃，证据不足时上层可拒答
    RAG_MIN_SCORE: float = 0.15
    # 本地哈希向量是词面匹配：查询双字词覆盖率低于该值时视为无证据
    RAG_MIN_COVERAGE: float = 0.15
    RAG_RERANK_ENABLED: bool = True
    # AI 配置均为可选；不配置 Key 时系统使用本地知识库回答。
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    # 可选：智谱 4.5 系列设为 "disabled" 可关闭思考模式，首字延迟从十几秒降到 1 秒内；
    # 其他厂商（OpenAI 等）不认识该参数，保持留空。
    OPENAI_THINKING: str = ""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 其他文件通过 settings 读取配置
settings = Settings()
