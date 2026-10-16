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
