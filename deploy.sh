#!/usr/bin/env bash
# ============================================================================
#  AI-PM 一键部署脚本（完整版）
#  用途：把本地全部改动（后端源码 + 前端构建产物）同步到生产服务器并重启服务
#  前置：~/.ssh/config 已配置 Host 81.70.158.130 (User root, Port 7000)，
#        且本机持有可登录的私钥（或已配置 agent 转发）。
#  用法：bash deploy.sh
# ============================================================================
set -e

cd "$(dirname "$0")"

# ---- 服务器配置（与 ~/.ssh/config 的 Host 一致）----
REMOTE_USER="root"
REMOTE_HOST="81.70.158.130"
REMOTE_DIR="/opt/AI-PM-Installer"   # 远端的项目根目录（如不同请修改）

echo "===== [1/4] 构建前端 ====="
cd frontend
npx vite build
cd ..

echo "===== [2/4] 同步后端源码（排除 venv/缓存/密钥/数据库）====="
rsync -avz --delete \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='.env' \
  --exclude='*.db' \
  --exclude='logs' \
  --exclude='uploads' \
  backend/app/ \
  $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/backend/app/

echo "===== [3/4] 同步前端构建产物 ====="
rsync -avz --delete \
  frontend/dist/ \
  $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/frontend/dist/

echo "===== [4/4] 重启服务并自检 ====="
ssh $REMOTE_USER@$REMOTE_HOST bash -s <<'REMOTE'
  set -e
  # 自动识别 systemd 服务名（sync 脚本写的是 ai-pm，部署文档写的是 aipm）
  SVC=""
  if systemctl list-unit-files 2>/dev/null | grep -q "^ai-pm.service"; then SVC="ai-pm"; fi
  if [ -z "$SVC" ] && systemctl list-unit-files 2>/dev/null | grep -q "^aipm.service"; then SVC="aipm"; fi
  if [ -n "$SVC" ]; then
    echo "重启服务: $SVC"
    systemctl restart "$SVC"
    sleep 4
    systemctl is-active "$SVC" && echo "服务状态: active" || echo "服务状态: 非 active，请检查日志"
  else
    echo "未找到 systemd 服务，尝试直接重启 uvicorn（如用 nohup 启动）"
    pkill -f "serve.py" 2>/dev/null || true
    sleep 2
    cd /opt/AI-PM-Installer/backend && (setsid venv/bin/python serve.py >/tmp/aipm.log 2>&1 &) || true
    sleep 4
  fi
  echo "--- 健康检查 ---"
  curl -sk -m 8 -o /dev/null -w "HTTPS / -> %{http_code}\n" https://127.0.0.1/ || true
  curl -sk -m 8 -o /dev/null -w "HTTP  /health -> %{http_code}\n" http://127.0.0.1:8000/health || true
REMOTE

echo "===== 部署完成 ====="
echo "请本地验证: https://81.70.158.130/ 与 https://81.70.158.130/api/v1/dashboard/next-steps"
