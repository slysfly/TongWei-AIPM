#!/usr/bin/env bash
# 通维AI项目管理系统 (AI-PM) — 卸载脚本
# 停止服务、停用 systemd 单元、删除虚拟环境与运行产物（不删业务数据，除非加 --purge）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_DIR:-${BASH_SOURCE[0]}}")" && pwd)"
BK="$SCRIPT_DIR/backend"

PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1

echo "[卸载] 停止 ai-pm 服务 ..."
if command -v systemctl >/dev/null 2>&1 && [ -f /etc/systemd/system/ai-pm.service ]; then
  sudo systemctl disable --now ai-pm.service 2>/dev/null || true
  sudo rm -f /etc/systemd/system/ai-pm.service
  sudo systemctl daemon-reload 2>/dev/null || true
  echo "[卸载] 已停用并移除 systemd 单元"
else
  pkill -f "serve.py" 2>/dev/null && echo "[卸载] 已终止运行中的 serve.py" || echo "[卸载] 无运行中的进程"
fi

if [ "$PURGE" -eq 1 ]; then
  echo "[卸载] 删除虚拟环境与运行产物（保留源码与 .env）..."
  rm -rf "$BK/venv" "$BK/__pycache__" "$BK/logs" 2>/dev/null || true
  echo "[警告] 业务数据库（*.db）与 uploads/ 已保留；如需彻底清理请手动删除。"
else
  echo "[卸载] 仅停止服务，保留 venv / 数据库 / 配置（加 --purge 可彻底清理）"
fi
echo "[完成] 卸载结束。"
