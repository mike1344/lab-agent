"""Alembic 迁移入口：统一从 backend/.env 读取数据库连接，与应用共用一套配置。

常用命令（在 backend 目录下执行）：
    alembic upgrade head                          # 把数据库升级到最新表结构
    alembic revision --autogenerate -m "说明"     # 对比 ORM 模型与数据库，生成新迁移
    alembic stamp head                            # 老库（表已存在）只登记版本号，不执行 DDL
"""

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401 - 导入全部 ORM 模型，autogenerate 依赖这些元数据做对比
from app.config import settings
from app.database import Base

# 目标表结构：应用全部 ORM 模型的元数据
target_metadata = Base.metadata

# 数据库连接串复用应用的 .env 配置，避免 alembic.ini 与应用两处维护
DATABASE_URL = settings.DATABASE_URL


def run_migrations_offline() -> None:
    """离线模式：只把迁移渲染成 SQL 脚本，不连接数据库（alembic upgrade --sql）。"""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库并执行迁移。"""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
