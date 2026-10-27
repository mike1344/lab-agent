#!/usr/bin/env bash
# ============================================================
# 一键验证（Linux / macOS）：从空环境安装 → lint → 后端测试 → 前端测试与构建
#
# 用法（仓库根目录）：
#   ./scripts/verify.sh              # 全量
#   ./scripts/verify.sh --skip-frontend
#   ./scripts/verify.sh --skip-install
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKIP_INSTALL=0
SKIP_FRONTEND=0
for arg in "$@"; do
  case "$arg" in
    --skip-install) SKIP_INSTALL=1 ;;
    --skip-frontend) SKIP_FRONTEND=1 ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

echo "== 后端 =="
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
PY=".venv/bin/python"

if [ "$SKIP_INSTALL" -eq 0 ]; then
  "$PY" -m pip install --upgrade pip
  if [ -f requirements.txt ]; then
    "$PY" -m pip install -r requirements.txt
  else
    "$PY" -m pip install -r requirements-all.txt
  fi
fi

"$PY" -m ruff check .
"$PY" -m ruff format --check .
"$PY" -m unittest discover -s tests

if [ "$SKIP_FRONTEND" -eq 0 ]; then
  echo "== 前端 =="
  cd "$ROOT/fronted"
  [ "$SKIP_INSTALL" -eq 0 ] && npm ci
  npm test
  npm run build
fi

echo "全部检查通过 ✅"
