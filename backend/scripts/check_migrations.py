"""在临时 SQLite 上执行全部 Alembic 迁移，验证“空库 → 全量表结构”可复现。

为什么需要它：接口测试用 SQLAlchemy ``create_all`` 建表，会绕过 Alembic；
一旦迁移脚本写错（顺序、外键、server_default），线上执行 ``alembic upgrade head``
才会暴露。本脚本在临时库上完整跑一遍迁移并校验关键表存在，适合放进 CI。

用法（在 backend 目录执行）：
    .\\.venv\\Scripts\\python.exe scripts\\check_migrations.py
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

EXPECTED_TABLES = {
    "users",
    "labs",
    "equipment",
    "reservations",
    "announcements",
    "announcement_comments",
    "announcement_reads",
    "repairs",
    "notifications",
    "blackout_periods",
    "login_logs",
    "operation_logs",
    "favorites",
    "procurements",
    "courses",
    "course_enrollments",
    "agent_tool_logs",
}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lab_agent_migration_", ignore_cleanup_errors=True) as directory:
        database = Path(directory) / "migration_check.db"
        environment = {
            **os.environ,
            "DATABASE_URL": f"sqlite+pysqlite:///{database.as_posix()}",
            "JWT_SECRET_KEY": "migration-check-only",
        }
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=environment,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise SystemExit("Alembic 迁移执行失败")

        connection = sqlite3.connect(database)
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            connection.close()
        missing = EXPECTED_TABLES - tables
        if missing:
            raise SystemExit(f"迁移后缺少表：{sorted(missing)}")
        print(f"迁移验证通过：{len(tables)} 张表（含全部业务表）")


if __name__ == "__main__":
    main()
