# 通维 AI-PM 部署文档

> 版本：v1.0.0 | 最后更新：2026-07-18
> 配套文档：[管理员运维手册](./管理员运维手册.md)、[操作手册](./操作手册.md)

---

## 目录

1. [系统要求](#1-系统要求)
2. [快速部署（5分钟）](#2-快速部署5分钟)
3. [生产部署（Nginx反向代理 + SSL）](#3-生产部署nginx反向代理--ssl)
4. [环境变量说明](#4-环境变量说明)
5. [Docker 部署](#5-docker-部署)
6. [常见问题排查](#6-常见问题排查)

---

## 1. 系统要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Ubuntu 22.04 / CentOS 7 / Windows Server 2019+ | Ubuntu 24.04 LTS |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB RAM | 8 GB RAM |
| 磁盘 | 20 GB 可用空间 | 50 GB SSD |
| Python | 3.11+ | 3.12 |
| 数据库 | SQLite（内置） | PostgreSQL 15+ |
| 网络 | 可访问外网（首次安装依赖） | 可访问 AI API 服务 |
| Node.js | — | 20 LTS（如需自行构建前端） |

### 1.1 端口要求

| 端口 | 用途 | 说明 |
|------|------|------|
| 8000 | 主服务（API + 前端） | 默认 HTTP，生产通过 Nginx 代理 |
| 5432 | PostgreSQL | 生产数据库（可选） |
| 6379 | Redis | 缓存/队列（可选） |

---

## 2. 快速部署（5分钟）

### 2.1 下载安装包

从发布页面下载 `AI-PM-Installer-v1.0.0.zip`。

### 2.2 解压

```bash
# Linux
unzip AI-PM-Installer-v1.0.0.zip
cd AI-PM-Installer-v1.0.0

# Windows
# 右键解压到当前文件夹，进入 AI-PM-Installer-v1.0.0 目录
```

### 2.3 配置管理员密码（可选）

编辑 `backend/.env`，设置管理员密码（默认 `admin/admin123`，部署到公网前**必须修改**）：

```env
INITIAL_ADMIN_PASSWORD=你的强密码（≥12位，含大小写字母+数字+特殊字符）
```

### 2.4 启动系统

**Linux / macOS：**

```bash
bash start.sh
```

**Windows：**

双击 `启动.bat`（或用 PowerShell 运行 `启动.ps1`）

首次启动过程：
1. 自动创建 Python 虚拟环境
2. 自动安装依赖（约 2-5 分钟，需联网）
3. 自动初始化数据库（建表 + 创建管理员）
4. 启动 Web 服务在 http://localhost:8000

### 2.5 访问系统

| 入口 | 地址 |
|------|------|
| 管理界面 | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

默认账号：`admin` / `admin123`（首次登录后请修改密码）

---

## 3. 生产部署（Nginx反向代理 + SSL）

### 3.1 系统架构

```
用户浏览器
    │
    ▼
Nginx (443 HTTPS)
    │
    ▼ proxy_pass http://127.0.0.1:8000
    │
FastAPI 服务 (Uvicorn, 仅监听 127.0.0.1)
    │
    ├── PostgreSQL（数据库）
    ├── Redis（缓存/队列）
    └── 前端静态文件（内置）
```

### 3.2 Nginx 配置模板

```nginx
# /etc/nginx/sites-available/aipm.conf
upstream aipm_backend {
    server 127.0.0.1:8000;
    keepalive 64;
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name pm.your-company.com;
    return 301 https://$host$request_uri;
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name pm.your-company.com;

    # SSL 证书（见 3.3 节配置）
    ssl_certificate     /etc/letsencrypt/live/pm.your-company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pm.your-company.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # 安全头部
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # 客户端上传大小（与后端 MAX_UPLOAD_SIZE 一致，默认 100MB）
    client_max_body_size 100M;

    # API 代理
    location /api/ {
        proxy_pass http://aipm_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # 限制 API 文档在内网访问
    location /docs {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        proxy_pass http://aipm_backend;
    }

    # 限制监控接口在内网访问
    location /api/v1/monitoring/ {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        proxy_pass http://aipm_backend;
    }

    # 健康检查端点（无鉴权，用于负载均衡）
    location /health {
        proxy_pass http://aipm_backend;
    }

    # 前端静态页面
    location / {
        proxy_pass http://aipm_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 日志
    access_log /var/log/nginx/aipm_access.log;
    error_log  /var/log/nginx/aipm_error.log;
}
```

### 3.3 SSL 证书配置

#### 方式一：Let's Encrypt（推荐，免费自动续期）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 申请证书（自动配置 Nginx）
sudo certbot --nginx -d pm.your-company.com

# 测试自动续期
sudo certbot renew --dry-run

# 续期由 systemd 定时任务自动完成（certbot.timer）
```

#### 方式二：自签名证书（内网测试用）

```bash
# 生成私钥和自签名证书（有效期 365 天）
sudo mkdir -p /etc/ssl/aipm
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/aipm/aipm.key \
    -out /etc/ssl/aipm/aipm.crt \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Company/CN=pm.your-company.com"

# Nginx 引用路径
# ssl_certificate     /etc/ssl/aipm/aipm.crt;
# ssl_certificate_key /etc/ssl/aipm/aipm.key;
```

### 3.4 Systemd 服务配置

将服务注册为 systemd 服务，实现开机自启和进程守护。

```ini
# /etc/systemd/system/aipm.service
[Unit]
Description=通维 AI-PM 项目管理系统 v1.0.0
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=aipm
Group=aipm
WorkingDirectory=/opt/AI-PM-Installer/backend
ExecStart=/opt/AI-PM-Installer/backend/venv/bin/python serve.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=PORT=8000

# 安全配置
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo useradd -r -s /bin/false aipm
sudo mkdir -p /opt/AI-PM-Installer
# 将安装包解压到 /opt/AI-PM-Installer
sudo chown -R aipm:aipm /opt/AI-PM-Installer

sudo cp ai-pm.service /etc/systemd/system/aipm.service
sudo systemctl daemon-reload
sudo systemctl enable --now aipm

# 查看状态
sudo systemctl status aipm

# 查看日志
sudo journalctl -u aipm -f
```

### 3.5 生产安全配置清单

部署到生产环境前，请逐项确认：

- [ ] `ENVIRONMENT=production`（启用弱密钥校验）
- [ ] `SECRET_KEY` 设为强随机值（`openssl rand -hex 32`）
- [ ] `INITIAL_ADMIN_PASSWORD` 改为强密码
- [ ] 配置 PostgreSQL 数据库
- [ ] 配置 Redis（生产不要用 `memory://`）
- [ ] 配置至少一家 AI API Key
- [ ] Nginx 配置 HTTPS
- [ ] 限制 `/docs` 和 `/monitoring` 内网访问
- [ ] 配置数据库定期备份
- [ ] 配置 SMTP 邮件
- [ ] 备份 `FIELD_ENCRYPTION_KEY`

---

## 4. 环境变量说明

### 4.1 基础配置

| 变量名 | 默认值 | 必填 | 说明 |
|--------|-------|------|------|
| `ENVIRONMENT` | `development` | 是 | 运行环境：`development` / `production` |
| `VERSION` | `1.0.0` | 否 | 系统版本号 |
| `APP_NAME` | `通维AI项目管理系统` | 否 | 应用名称 |
| `PORT` | `8000` | 否 | 服务监听端口 |

### 4.2 安全配置

| 变量名 | 默认值 | 必填 | 说明 |
|--------|-------|------|------|
| `SECRET_KEY` | 自动生成 | **是** | JWT 签名密钥。生产环境必须显式设置强随机值（`openssl rand -hex 32`）。**弱密钥时生产环境会拒绝启动**。 |
| `FIELD_ENCRYPTION_KEY` | 从 `SECRET_KEY` 派生 | 推荐 | 字段级 AES-256-GCM 加密密钥。建议显式设置并离线备份，防止 `SECRET_KEY` 变更后加密数据无法解密。 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | 否 | JWT 访问令牌有效期（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 否 | 刷新令牌有效期（天） |

### 4.3 初始管理员配置

| 变量名 | 默认值 | 必填 | 说明 |
|--------|-------|------|------|
| `INITIAL_ADMIN_USERNAME` | `admin` | 否 | 初始管理员用户名（仅首次启动创建） |
| `INITIAL_ADMIN_PASSWORD` | `admin123` | **是** | 初始管理员密码。**部署到公网前务必修改为强密码** |
| `INITIAL_ADMIN_EMAIL` | `admin@example.com` | 否 | 初始管理员邮箱 |
| `INITIAL_ADMIN_FULL_NAME` | `系统管理员` | 否 | 初始管理员姓名 |

### 4.4 数据库配置

| 变量名 | 默认值 | 必填 | 说明 |
|--------|-------|------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./tw_ai_pms.db` | 是 | 数据库连接 URL |
| `DB_MIGRATE` | `False` | 否 | 是否启用 Alembic 迁移（生产推荐 `True`） |
| `DATABASE_POOL_SIZE` | `20` | 否 | 连接池大小（仅 PostgreSQL） |
| `DATABASE_MAX_OVERFLOW` | `10` | 否 | 连接池溢出上限（仅 PostgreSQL） |

**数据库 URL 示例：**

```env
# SQLite（开发/演示）
DATABASE_URL=sqlite+aiosqlite:///./tw_ai_pms.db

# PostgreSQL（生产）
DATABASE_URL=postgresql+asyncpg://aipm:your_password@localhost:5432/aipm
```

### 4.5 Redis 配置

| 变量名 | 默认值 | 必填 | 说明 |
|--------|-------|------|------|
| `REDIS_URL` | `memory://` | 否 | Redis 连接 URL。`memory://` 为内存模式（开发用）。生产用 `redis://localhost:6379/0` |

### 4.6 AI API Key 配置

系统支持 11 家 AI 模型提供商，至少配置一个 Key 才能使用 AI 功能。

| 变量名 | 说明 | 关联模型 |
|--------|------|---------|
| `MINIMAX_API_KEY` | MiniMax API Key（默认） | MiniMax-M2.7 |
| `OPENAI_API_KEY` | OpenAI API Key | GPT-4, GPT-3.5 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | deepseek-chat |
| `ANTHROPIC_API_KEY` | Anthropic API Key | Claude 3 |
| `BAIDU_API_KEY` + `BAIDU_SECRET_KEY` | 百度文心一言 | ERNIE |
| `ALIYUN_API_KEY` | 阿里通义千问 | Qwen |
| `TENCENT_API_KEY` | 腾讯混元 | Hunyuan |
| `ZHIPU_API_KEY` | 智谱 GLM | GLM-4 |
| `MOONSHOT_API_KEY` | Moonshot Kimi | moonshot |
| `QWEN_API_KEY` | 通义千问（独立配置） | Qwen-Max |
| `SILICONFLOW_API_KEY` | 硅基流动 | 多种开源模型 |
| `OPENAI_COMPATIBLE_API_KEY` + `OPENAI_COMPATIBLE_BASE_URL` | 自定义 OpenAI 兼容 API | 自定义 |

**LLM 模型配置：**

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `LLM_MODEL` | `MiniMax-M2.7` | 默认 AI 模型名称 |
| `LLM_TEMPERATURE` | `0.7` | 生成温度（0.0-2.0） |
| `LLM_MAX_TOKENS` | `4000` | 最大生成 Token 数 |

> **注意**：AI Key 也可以在「系统设置 → 大模型配置」页面中填写，两者等效。

### 4.7 邮件配置

| 变量名 | 默认值 | 必填 | 说明 |
|--------|-------|------|------|
| `SMTP_HOST` | `smtp.gmail.com` | 否 | SMTP 服务器地址 |
| `SMTP_PORT` | `587` | 否 | SMTP 端口 |
| `SMTP_USER` | 空 | 否 | SMTP 用户名 |
| `SMTP_PASSWORD` | 空 | 否 | SMTP 密码 |
| `EMAILS_FROM` | `noreply@tongweizx.com` | 否 | 发件人地址 |

未配置 SMTP 时，邮件功能优雅降级，不影响其他功能。

### 4.8 CORS 与上传配置

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173,...` | 允许跨域的前端来源（逗号分隔） |
| `UPLOAD_DIR` | `./uploads` | 上传文件存储目录 |
| `MAX_UPLOAD_SIZE` | `104857600` (100MB) | 单文件上传大小上限（字节） |

### 4.9 日志配置

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `LOG_LEVEL` | `INFO` | 日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR` |

### 4.10 分页与缓存

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `DEFAULT_PAGE_SIZE` | `20` | 默认每页条数 |
| `MAX_PAGE_SIZE` | `100` | 最大每页条数 |
| `CACHE_TTL` | `300` | 缓存过期时间（秒） |
| `CACHE_ENABLED` | `true` | 是否启用缓存 |

### 4.11 集成配置

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `FEISHU_APP_ID` | 空 | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 空 | 飞书应用 App Secret |
| `ZAPIER_WEBHOOK_SECRET` | 空 | Zapier Webhook 签名密钥 |
| `CELERY_BROKER_URL` | `sync+memory://` | Celery 任务队列地址 |
| `CELERY_RESULT_BACKEND` | `cache+memory://` | Celery 结果后端 |

---

## 5. Docker 部署

### 5.1 前提条件

- Docker Engine 24+
- Docker Compose V2

### 5.2 快速启动

```bash
# 1. 进入安装包目录
cd AI-PM-Installer-v1.0.0

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少配置 SECRET_KEY 和 INITIAL_ADMIN_PASSWORD

# 3. 启动服务
docker compose up -d --build

# 4. 查看日志
docker compose logs -f
```

### 5.3 常用命令

```bash
# 启动
docker compose up -d

# 停止
docker compose down

# 重启
docker compose restart

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f backend

# 进入容器
docker compose exec backend bash

# 重建镜像并启动
docker compose up -d --build

# 清理数据（删除数据卷）
docker compose down -v
```

### 5.4 Docker 部署说明

- 内置 PostgreSQL + Redis，无需额外安装
- 数据卷 `pgdata` 持久化数据库
- 数据卷 `uploads` 持久化上传文件
- `restart: unless-stopped` 保证进程退出后自动拉起
- 生产务必通过环境变量覆盖 `SECRET_KEY` 为强随机值

---

## 6. 常见问题排查

### 6.1 服务无法启动

| 现象 | 可能原因 | 解决方案 |
|------|---------|---------|
| 启动立即退出，日志报"弱 SECRET_KEY" | 生产模式下使用了默认密钥 | 生成强随机密钥：`openssl rand -hex 32`，设入 `SECRET_KEY` 后重启 |
| 端口 8000 被占用 | 其他进程占用端口 | 改端口启动：`PORT=9000 python serve.py`，或查找并释放端口 |
| Python 版本太低 | 系统 Python < 3.11 | `python3 --version` 检查，安装 Python 3.11+ |
| 依赖安装失败 | 网络问题 / pip 源不可达 | 使用国内镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 页面空白 / 404 | 前端产物缺失 | 确认 `backend/frontend/` 或 `frontend/dist/` 目录存在 |
| `sqlite3.OperationalError: no such table` | 数据库未正确初始化 | 删除 `backend/*.db` 后重启，或执行 `alembic upgrade head` |

**启动诊断命令：**

```bash
# 检查 Python 版本
python --version

# 直接运行后端（查看详细错误）
cd backend
python serve.py

# 检查 SQLite 数据库
sqlite3 backend/tw_ai_pms.db ".tables"

# 检查配置文件
cat backend/.env | grep -v "^#" | grep -v "^$"
```

### 6.2 Agent 全部离线

| 可能原因 | 解决方案 |
|---------|---------|
| Redis 未启动（生产模式） | 启动 Redis：`sudo systemctl start redis`，或临时切回 `REDIS_URL=memory://` |
| Celery Worker 未启动 | 确认 `celery worker` 进程运行中 |
| 代理网络不通 | 检查系统代理设置，确保 AI Agent 可访问外网 |
| 数据库连接超时 | 检查 `DATABASE_URL` 配置，使用 `monitoring/health` 接口确认数据库状态 |

**诊断步骤：**

```bash
# 1. 检查健康状态
curl http://localhost:8000/api/v1/monitoring/health

# 2. 查看错误日志
tail -100 backend/logs/error.log

# 3. 检查 Redis 连接
redis-cli ping

# 4. 检查数据库连接
# SQLite
sqlite3 backend/tw_ai_pms.db "SELECT count(*) FROM users;"

# PostgreSQL
psql -h localhost -U aipm -d aipm -c "SELECT count(*) FROM users;"
```

### 6.3 AI 调用超时

| 可能原因 | 解决方案 |
|---------|---------|
| 未配置 AI API Key | 在「系统设置 → 大模型配置」中填写至少一家 AI 厂商的 API Key |
| API Key 无效或额度耗尽 | 检查 API Key 有效期和余额；尝试其他 AI 提供商 |
| 网络无法访问 AI 服务 | 检查服务器能否访问外网；配置代理环境变量（如 `HTTP_PROXY`） |
| 超时时间过短 | 增加 `LLM_MAX_TOKENS` 或通过代码调整超时参数 |
| AI 服务本身故障 | 切换其他模型试试；查看 AI 服务商状态页面 |

**诊断步骤：**

```bash
# 1. 测试 AI 连接（需要 Python 环境）
cd backend
source venv/bin/activate
python -c "
import httpx
r = httpx.get('https://api.minimax.chat/v1/status', timeout=10)
print('AI 服务状态:', r.status_code)
"

# 2. 检查环境变量中 AI Key 是否正确
grep -E "(_API_KEY|LLM_MODEL)" backend/.env

# 3. 通过 API 测试 AI 功能
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(你的登录Token)" \
  -d '{"message":"你好","stream":false}'
```

### 6.4 数据库问题

| 问题 | 解决方案 |
|------|---------|
| 数据库无法连接 | 检查 `DATABASE_URL` 配置和数据库服务状态 |
| 迁移版本冲突 | `alembic check` 检查一致性；必要时 `DB_MIGRATE=0` 用 `create_all` 兜底 |
| SQLite 数据库损坏 | 用 `sqlite3 pms.db ".recover"` 抢救，然后恢复备份 |
| 忘记管理员密码 | 删除超级用户行后重启（系统重建），或用脚本重置 bcrypt 哈希 |

### 6.5 性能问题

| 问题 | 解决方案 |
|------|---------|
| 接口响应慢 | 检查 `monitoring/slow-queries` 查看慢查询；增加数据库连接池大小 |
| AI 响应慢 | 切换更快的模型；检查网络延迟 |
| 上传文件慢 | 检查 `MAX_UPLOAD_SIZE`；使用 CDN 或对象存储加速 |

---

## 附录：快速参考

### 常用命令速查

```bash
# 启动
bash start.sh                    # Linux
双击 启动.bat                     # Windows

# 健康检查
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/monitoring/health

# 生成密钥
openssl rand -hex 32

# 数据库备份（SQLite）
sqlite3 backend/pms.db ".backup 'backup/pms_hot.db'"

# 数据库迁移
cd backend && alembic upgrade head

# 改端口启动
PORT=9000 python serve.py

# 生产启动
systemctl start aipm
systemctl enable aipm
journalctl -u aipm -f

# Docker
docker compose up -d --build
docker compose down
```

### 配置文件路径

| 用途 | 路径 |
|------|------|
| 环境变量 | `backend/.env` |
| 环境变量模板 | `backend/.env.example` |
| Nginx 配置 | `/etc/nginx/sites-available/aipm.conf` |
| Systemd 服务 | `/etc/systemd/system/aipm.service` |
| SQLite 数据 | `backend/pms.db` 或 `backend/tw_ai_pms.db` |
| 日志 | `backend/logs/app.log`、`backend/logs/error.log` |
| 上传文件 | `backend/uploads/` |
| 迁移脚本 | `backend/alembic/versions/` |

---

*通维 AI-PM v1.0.0 部署文档 | 2026-07-18*
