#!/bin/bash
# 生产库即时快照脚本 —— 在任何写操作前调用，留底后可回滚。
# 用法: /opt/backups/backup_now.sh
set -e
SRC="/opt/AI-PM/backend/test.db"
DST_DIR="/opt/backups/db"
LOG="$DST_DIR/md5.log"
TS="$(date +%Y%m%d_%H%M%S)"
RETAIN_DAYS=30

mkdir -p "$DST_DIR"

if [ -f "$SRC" ]; then
  cp -p "$SRC" "$DST_DIR/test_${TS}.db"
  md5sum "$DST_DIR/test_${TS}.db" >> "$LOG"
  echo "BACKUP_OK $DST_DIR/test_${TS}.db"
else
  echo "SRC_MISSING $SRC"
  exit 1
fi

# 清理超过保留期的旧快照（>30 天），确保保留期满足 >7 天要求
DELETED=$(find "$DST_DIR" -name 'test_*.db' -mtime +"$RETAIN_DAYS" -print -delete | wc -l)
echo "PRUNE_DONE retain_days=$RETAIN_DAYS removed=$DELETED"

# 当前在留快照数
echo "CURRENT_SNAPSHOTS=$(find "$DST_DIR" -name 'test_*.db' | wc -l)"
