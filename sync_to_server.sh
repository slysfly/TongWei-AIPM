#!/usr/bin/env bash
set -e

echo "===== AI-PM Phase3 同步脚本 ====="

# 配置远程服务器
REMOTE_USER="root"
REMOTE_HOST="your-server-ip"
REMOTE_DIR="/opt/AI-PM-Installer"

# 1. 后端文件同步
echo "[1/3] 同步后端代码..."
rsync -avz --delete \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  backend/app/api/v1/ai_monitor.py \
  backend/app/api/routers.py \
  backend/app/services/ai/out_of_box_agents.py \
  $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/backend/app/

# 2. 前端构建产物同步
echo "[2/3] 同步前端构建产物..."
cd frontend
npx vite build
rsync -avz --delete dist/ $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/frontend/dist/
cd ..

# 3. 重启服务
echo "[3/3] 重启服务..."
ssh $REMOTE_USER@$REMOTE_HOST "systemctl restart ai-pm"

echo "===== 同步完成 ====="
