#!/usr/bin/env bash
# 每日数据库备份：卡密/余量/流水就是钱，丢库=集体退款。
# crontab 示例（每天 4 点）: 0 4 * * * /path/to/deer-flow/scripts/backup_db.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/deerflow-backups}"
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d-%H%M%S)

URL="${PLATFORM_DATABASE_URL:-sqlite+aiosqlite:///./deerflow_platform.db}"

if [[ "$URL" == postgresql* ]]; then
  # postgresql+asyncpg://user:pass@host:port/db → pg_dump 连接串
  PG_URL="${URL/+asyncpg/}"
  pg_dump "$PG_URL" | gzip > "$BACKUP_DIR/platform-$STAMP.sql.gz"
else
  DB_FILE="${URL#sqlite+aiosqlite:///}"
  sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/platform-$STAMP.db'"
  gzip "$BACKUP_DIR/platform-$STAMP.db"
  if [[ -f "deerflow_checkpoints.db" ]]; then
    sqlite3 deerflow_checkpoints.db ".backup '$BACKUP_DIR/checkpoints-$STAMP.db'"
    gzip "$BACKUP_DIR/checkpoints-$STAMP.db"
  fi
fi

# 只保留最近 30 份
ls -t "$BACKUP_DIR" | tail -n +31 | while read -r f; do rm -f "$BACKUP_DIR/$f"; done
echo "backup done: $BACKUP_DIR/platform-$STAMP"
