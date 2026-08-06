#!/usr/bin/env bash
# =============================================================
# 通维AI项目管理系统 (AI-PM) — 全新 Linux 一键安装器
# -------------------------------------------------------------
# 设计目标：解压发布包到任意全新 Linux 后，一条命令完成全部部署。
#   · 零外部依赖模式（默认）：SQLite + 内存 Redis/Celery，无需安装数据库/中间件
#   · 可选 PostgreSQL 模式：在 backend/.env 配置 DATABASE_URL 后自动启用
#
# 用法：
#   bash install.sh                                   # 交互式（自动生成随机密钥，默认管理员口令 admin123）
#   AIPM_ADMIN_PASSWORD='Str0ng#Passw0rd' bash install.sh   # 非交互，指定管理员强口令
#   bash install.sh --pg                              # 使用 .env 中已配置的 PostgreSQL（需先建好库）
#   bash install.sh --build                           # 额外用 npm 重新构建前端（需 Node 18+，默认用包内 dist）
#   bash install.sh --no-service                      # 不注册 systemd，直接前台运行（调试/容器用）
#
# 完成后访问：http://<服务器IP>:8000  （默认账号 admin / 您设置的口令）
# =============================================================
set -euo pipefail

# ---------- 颜色 ----------
if [ -t 1 ]; then
  C_GREEN=$'\033[0;32m'; C_YEL=$'\033[0;33m'; C_RED=$'\033[0;31m'; C_CYAN=$'\033[0;36m'; C_RST=$'\033[0m'
else
  C_GREEN=""; C_YEL=""; C_RED=""; C_CYAN=""; C_RST=""
fi
info(){ echo "${C_CYAN}[信息]${C_RST} $*"; }
ok(){ echo "${C_GREEN}[完成]${C_RST} $*"; }
warn(){ echo "${C_YEL}[注意]${C_RST} $*"; }
err(){ echo "${C_RED}[错误]${C_RST} $*"; }

# ---------- 权限（root 直接运行则无需 sudo） ----------
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# ---------- 参数 ----------
USE_PG=0; BUILD_FE=0; NO_SERVICE=0
for a in "$@"; do
  case "$a" in
    --pg) USE_PG=1;;
    --build) BUILD_FE=1;;
    --no-service) NO_SERVICE=1;;
    -h|--help) sed -n '3,20p' "$0"; exit 0;;
    *) warn "未知参数: $a（已忽略）";;
  esac
done

# ---------- 路径 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
[ -d "$BACKEND_DIR" ] || { err "未找到 backend/ 目录，请在发布包根目录运行 install.sh"; exit 1; }

# ---------- 检测系统 ----------
info "检测操作系统 ..."
if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS_ID="${ID:-linux}"
else
  OS_ID="linux"
fi
info "系统: ${PRETTY_NAME:-$OS_ID}"

# ---------- Python 检测 (>=3.11) ----------
info "检测 Python 3.11+ ..."
PY=""
for cand in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    ver=$("$cand" -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>/dev/null || echo "0.0")
    maj=$(echo "$ver" | cut -d. -f1); min=$(echo "$ver" | cut -d. -f2)
    if [ "$maj" -gt 3 ] || { [ "$maj" -eq 3 ] && [ "$min" -ge 11 ]; }; then
      PY="$cand"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  err "未找到 Python 3.11+。请先安装："
  case "$OS_ID" in
    ubuntu|debian) echo "    $SUDO apt-get update && $SUDO apt-get install -y python3.11 python3.11-venv python3.11-dev";;
    centos|rhel|fedora|rocky|almalinux) echo "    $SUDO dnf install -y python3.11 python3.11-devel";;
    *) echo "    请安装 Python 3.11 或更高版本";;
  esac
  exit 1
fi
info "使用 $PY ($($PY --version 2>&1))"

# ---------- 系统依赖（python-magic 需要 libmagic） ----------
info "安装运行时系统依赖（libmagic）..."
if command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update -qq >/dev/null 2>&1 || true
  $SUDO apt-get install -y libmagic1 curl >/dev/null 2>&1 || warn "libmagic1/curl 安装失败（python-magic 运行时可能报错，可手动安装）"
elif command -v dnf >/dev/null 2>&1; then
  $SUDO dnf install -y file-libs >/dev/null 2>&1 || warn "file-libs 安装失败"
elif command -v yum >/dev/null 2>&1; then
  $SUDO yum install -y file-libs >/dev/null 2>&1 || warn "file-libs 安装失败"
fi

# ---------- 配置 .env ----------
info "准备 backend/.env ..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  ok "已从模板生成 .env"
else
  warn "backend/.env 已存在，保留现有配置（不会覆盖）"
fi

# 生成随机 SECRET_KEY（若为空）并设置管理员口令
ADMIN_PW="${AIPM_ADMIN_PASSWORD:-}"
$PY - "$BACKEND_DIR/.env" "$ADMIN_PW" <<'PY'
import re, secrets, sys, os
path, admin_pw = sys.argv[1], sys.argv[2]
s = open(path, encoding="utf-8").read()
# SECRET_KEY
if re.search(r'^SECRET_KEY=\s*$', s, re.M) or 'SECRET_KEY=' not in s:
    key = secrets.token_hex(32)
    if re.search(r'^SECRET_KEY=', s, re.M):
        s = re.sub(r'^SECRET_KEY=.*$', f'SECRET_KEY={key}', s, flags=re.M)
    else:
        s = s.rstrip() + f"\nSECRET_KEY={key}\n"
# 管理员口令（非交互模式下才覆盖）
if admin_pw:
    if re.search(r'^INITIAL_ADMIN_PASSWORD=', s, re.M):
        s = re.sub(r'^INITIAL_ADMIN_PASSWORD=.*$', f'INITIAL_ADMIN_PASSWORD={admin_pw}', s, flags=re.M)
    else:
        s = s.rstrip() + f"\nINITIAL_ADMIN_PASSWORD={admin_pw}\n"
open(path, "w", encoding="utf-8").write(s)
PY
ok "SECRET_KEY 已就绪"

# 数据库模式
DB_URL=$(grep -E '^DATABASE_URL=' "$BACKEND_DIR/.env" | tail -1 | cut -d= -f2-)
if echo "$DB_URL" | grep -qi '^postgresql'; then
  USE_PG=1
  info "检测到 PostgreSQL 配置：$DB_URL"
else
  info "使用默认 SQLite（零依赖、无需数据库）"
fi

# 若强制 --pg 但仍是 sqlite，提示
if [ "$USE_PG" -eq 1 ] && ! echo "$DB_URL" | grep -qi '^postgresql'; then
  warn "--pg 已指定，但 .env 中 DATABASE_URL 仍是 SQLite；请先编辑 backend/.env 填入 PostgreSQL 连接串。"
fi

# PostgreSQL：尝试创建数据库（best-effort）
if [ "$USE_PG" -eq 1 ]; then
  info "PostgreSQL 模式：尝试确保目标数据库存在 ..."
  # 从 URL 解析 user/password/host/port/db
  u=$(echo "$DB_URL" | sed -E 's#postgresql\+asyncpg://##; s#postgresql://##')
  db=$(echo "$u" | sed -E 's#.*/##')
  auth=$(echo "$u" | sed -E 's#/.*##')
  host=$(echo "$auth" | sed -E 's#@.*##; s#.*@##; s#:.*##')
  port=$(echo "$auth" | grep -Eo ':[0-9]+' | tr -d ':' || echo 5432)
  user=$(echo "$auth" | sed -E 's#@.*##; s#:.*##')
  pass=$(echo "$auth" | sed -E 's#@.*##; s#^.*:##')
  if command -v psql >/dev/null 2>&1; then
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -tc "SELECT 1 FROM pg_database WHERE datname='$db'" | grep -q 1 \
      || PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -c "CREATE DATABASE \"$db\"" >/dev/null 2>&1 \
      && ok "数据库 '$db' 已就绪" || warn "无法自动创建数据库 '$db'，请确认 PostgreSQL 已启动且凭据正确"
  else
    warn "未找到 psql 客户端，跳过自动建库；请确保数据库 '$db' 已存在"
  fi
fi

# ---------- 虚拟环境 + 依赖 ----------
# 确保 venv 模块可用（部分最小化系统只装了 python 没装 venv 包）
if ! "$PY" -m venv --help >/dev/null 2>&1; then
  info "安装 Python venv 模块 ..."
  if command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get install -y "python${maj}.${min}-venv" "python${maj}.${min}-dev" >/dev/null 2>&1 \
      || warn "venv 模块安装失败，请手动安装 python${maj}.${min}-venv"
  elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y "python${maj}.${min}-devel" >/dev/null 2>&1 \
      || warn "venv 模块安装失败，请手动安装 python${maj}.${min}-devel"
  fi
fi

cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
  info "创建虚拟环境 ..."
  "$PY" -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
info "升级 pip 并安装后端依赖（首次约 2-5 分钟，需联网）..."
pip install --upgrade pip -q
if pip install -r requirements.txt -q; then
  ok "后端依赖安装完成"
else
  warn "主源安装失败，尝试清华镜像 ..."
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || { err "依赖安装失败，请检查网络"; exit 1; }
fi

# ---------- 前端（可选构建） ----------
if [ "$BUILD_FE" -eq 1 ]; then
  if [ -d "$FRONTEND_DIR" ] && command -v npm >/dev/null 2>&1; then
    info "重新构建前端 ..."
    cd "$FRONTEND_DIR"
    npm install >/dev/null 2>&1 && npm run build >/dev/null 2>&1 && ok "前端已重新构建" || warn "前端构建失败，将使用包内已构建的 dist"
    cd "$BACKEND_DIR"
  else
    warn "未找到 frontend/ 或 npm，跳过构建（使用包内 dist）"
  fi
else
  if [ -d "$FRONTEND_DIR/dist" ]; then
    ok "使用包内已构建前端 dist/"
  else
    warn "未找到 frontend/dist，请用 --build 重新构建前端"
  fi
fi

# ---------- 启动 / 注册服务 ----------
HOST="${AIPM_HOST:-0.0.0.0}"
PORT="${AIPM_PORT:-8000}"
RUN_USER="$(id -un)"

start_foreground(){
  info "以前台模式启动（Ctrl+C 停止）..."
  exec venv/bin/python serve.py
}

start_service(){
  info "注册 systemd 服务 ..."
  UNIT=/etc/systemd/system/ai-pm.service
  $SUDO tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=通维AI项目管理系统 (AI-PM)
After=network.target$([ "$USE_PG" -eq 1 ] && echo " postgresql.service")

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$BACKEND_DIR
ExecStart=$BACKEND_DIR/venv/bin/python serve.py
Environment=HOST=$HOST
Environment=PORT=$PORT
Restart=always
RestartSec=3
MemoryMax=2G
StandardOutput=journalctl
StandardError=journalctl

[Install]
WantedBy=multi-user.target
EOF
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable --now ai-pm.service
  sleep 4
  if systemctl is-active --quiet ai-pm.service; then
    ok "ai-pm 服务已启动"
  else
    err "服务启动失败，查看日志: $SUDO journalctl -u ai-pm -n 50"
    exit 1
  fi
}

if [ "$NO_SERVICE" -eq 1 ]; then
  start_foreground
else
  if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
    start_service
  else
    warn "当前环境无 systemd（容器？），改用 nohup 后台运行 ..."
    nohup venv/bin/python serve.py > "$BACKEND_DIR/logs/ai-pm.log" 2>&1 &
    sleep 4
    ok "已在后台启动（日志: $BACKEND_DIR/logs/ai-pm.log）"
  fi
fi

# ---------- 健康检查 ----------
info "执行健康检查 ..."
for i in $(seq 1 15); do
  code=$(curl -s -m 3 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/health" 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then break; fi
  sleep 2
done
if [ "$code" = "200" ]; then
  ok "健康检查通过 (HTTP 200)"
else
  warn "健康检查未返回 200（当前 $code），服务可能仍在初始化，请稍后访问"
fi

echo ""
echo "  ┌──────────────────────────────────────────────────────────┐"
echo "  │  安装完成！                                               │"
echo "  │  管理界面:  http://$(hostname -I 2>/dev/null | awk '{print $1}'):$PORT"
echo "  │  API 文档:  http://localhost:$PORT/docs                    │"
echo "  │  默认账号:  admin / ${AIPM_ADMIN_PASSWORD:-admin123}       │"
echo "  │  AI 功能:   到「系统设置 → 大模型配置」填入任一厂商 Key 启用 │"
echo "  └──────────────────────────────────────────────────────────┘"
