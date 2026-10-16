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
