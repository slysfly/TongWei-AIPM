#!/bin/bash
# 通维AI项目管理系统 - 一键启动脚本（Linux/macOS）
# 用法: chmod +x start.sh && ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/backend"

echo "=========================================="
echo "  通维AI项目管理系统 - 安装启动"
echo "=========================================="

# 1. 检查 Python
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "[ERROR] 未找到 Python 3，请先安装 Python 3.11+"
    exit 1
fi
echo "[OK] Python: $($PYTHON --version)"

# 2. 检查/创建虚拟环境
if [ ! -d "venv" ]; then
    echo "[..] 创建虚拟环境..."
    $PYTHON -m venv venv
fi
source venv/bin/activate

# 3. 安装依赖
echo "[..] 安装依赖..."
pip install -r requirements.txt -q 2>/dev/null
echo "[OK] 依赖安装完成"

# 4. 配置环境
if [ ! -f ".env" ]; then
    echo "[..] 从 .env.example 创建 .env..."
    cp .env.example .env
    echo "[WARN] 请编辑 backend/.env 修改 SECRET_KEY 和 LLM API Keys"
fi

# 5. 初始化数据库
echo "[..] 初始化数据库..."
$PYTHON -c "
import asyncio
from app.core.migrate import apply_migrations
asyncio.run(apply_migrations())
print('[OK] 数据库初始化完成')
"

# 6. 启动服务
echo ""
echo "=========================================="
echo "  🚀 启动服务..."
echo "  访问: http://localhost:8000"
echo "=========================================="
$PYTHON serve.py
