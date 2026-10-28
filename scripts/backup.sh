#!/usr/bin/env bash
# ============================================================
# 每日备份脚本：MySQL 全量导出 + uploads 数据卷打包，默认保留 30 天
#
# 用法：
#   ./scripts/backup.sh [备份目录，默认 ./backups]
#
# 建议放到宿主机 crontab（每天 03:00）：
#   0 3 * * * cd /opt/lab_agent && ./scripts/backup.sh /data/backups >> /var/log/lab_agent_backup.log 2>&1
#
# 环境变量：
#   MYSQL_ROOT_PASSWORD  MySQL root 密码（不填则读仓库根目录 .env）
#   RETENTION_DAYS       保留天数（默认 30）
#   COMPOSE              容器编排命令（默认 "docker compose"）
# ============================================================
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPOSE="${COMPOSE:-docker compose}"

cd "$(dirname "$0")/.."
mkdir -p "$BACKUP_DIR"

STAMP=$(date +%F_%H%M%S)
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-$(grep -E '^MYSQL_ROOT_PASSWORD=' .env 2>/dev/null | cut -d= -f2- || true)}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-lab_agent_root_pwd}"

echo "[1/2] 导出数据库 → ${BACKUP_DIR}/db_${STAMP}.sql.gz"
$COMPOSE exec -T mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction lab_agent' \
  | gzip > "${BACKUP_DIR}/db_${STAMP}.sql.gz"

echo "[2/2] 打包 uploads 数据卷 → ${BACKUP_DIR}/uploads_${STAMP}.tgz"
docker run --rm -v lab_agent_uploads_data:/data -v "$(pwd)/${BACKUP_DIR}":/backup alpine \
  tar czf "/backup/uploads_${STAMP}.tgz" -C /data .

echo "清理 ${RETENTION_DAYS} 天前的旧备份"
find "$BACKUP_DIR" -name 'db_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name 'uploads_*.tgz' -mtime +"$RETENTION_DAYS" -delete

echo "备份完成：${BACKUP_DIR}（保留 ${RETENTION_DAYS} 天）"
