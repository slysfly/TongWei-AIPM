# 通维咨询AI项目管理系统 — 安装部署指南

> 包名：TW-AIPM-v0.0.1-202607200108
> 发布日期：2026-07-20

---

## 目录结构

```
TW-AIPM-v0.0.1/
├── backend/                    # 后端源码（FastAPI + SQLAlchemy）
│   ├── app/                    # 应用代码
│   │   ├── api/                # API 路由层
│   │   ├── core/               # 核心服务（鉴权/安全/响应格式）
│   │   ├── db/                 # 数据库会话
│   │   ├── middleware/         # 中间件（监控/安全/响应格式）
│   │   ├── models/             # 数据模型（SQLAlchemy ORM）
│   │   └── services/           # 业务服务层
│   ├── alembic/                # 数据库迁移
│   ├── serve.py                # 生产启动入口
│   ├── main.py                 # 开发启动入口
│   ├── requirements.txt        # 生产依赖
│   ├── requirements-dev.txt    # 开发依赖
│   └── .env.example            # 环境变量模板
├── frontend/
│   ├── dist/                   # 构建产物（可直接部署）
│   └── src/                    # 前端源码（React + TypeScript）
├── scripts/
│   ├── smoke_e2e.py            # 端到端冒烟测试脚本
│   └── diag_schema.py          # 数据库 Schema 诊断
├── deploy_paramiko.py          # 远程部署脚本
├── run_smoke.py                # 冒烟测试本地编排
└── README-install.md           # 本文件
```

## 环境要求

- **操作系统**: Linux（CentOS 7+ / Ubuntu 20.04+）/ macOS / Windows
- **Python**: 3.11+
- **Node.js**: 22+（仅开发构建时需要）
- **数据库**: SQLite（开发）/ PostgreSQL 15+（生产）
- **内存**: ≥ 4GB（推荐 8GB+，含 LLM 推理）

## 安装步骤

### 1. 解压安装包

```bash
unzip TW-AIPM-v0.0.1-202607200108.zip -d /opt/AI-PM
cd /opt/AI-PM
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，修改以下关键配置：
# - SECRET_KEY：生成随机密钥
# - DATABASE_URL：数据库连接串
# - LLM 相关配置（Provider/API Key）
```

### 3. 安装后端依赖

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 初始化数据库

```bash
python -m app.core.migrate   # 自动执行 Alembic 迁移 + create_all 兜底
```

### 5. 启动服务

```bash
# 生产模式
python serve.py

# 开发模式
main.py
```

服务启动后访问 http://localhost:8000

### 6. 一键启动（新系统快速体验）

```bash
# Linux / macOS
chmod +x start.sh && ./start.sh

# Windows
双击 start.bat
```

启动脚本会自动：创建 venv → 安装依赖 → 生成 .env → 初始化数据库 → 启动服务。

### 7. 生产部署（systemd）

```bash
# 使用 ai-pm.service 注册为系统服务
sudo cp ai-pm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-pm
sudo systemctl start ai-pm
```

### 8. 部署到远程服务器

```bash
AIPM_PASS='your_password' python deploy_paramiko.py push
```

## 功能验证

### 冒烟测试

```bash
AIPM_PASS='your_password' python run_smoke.py
```

预期输出：
- ✅ WS 实时事件推送（task_progress / task_done）
- ✅ analyze_project → success
- ✅ summarize_lessons → success（AI 生成经验教训）
- ✅ RESULT: PASS

### 健康检查

```bash
curl http://localhost:8000/health
curl -k https://localhost/
```

## 版本亮点

| 功能 | 说明 |
|------|------|
| 🤖 AI 项目经理 | 自然语言 → WBS 分解 / 风险预测 / 经验教训自动沉淀 |
| 👥 多 Agent 协作 | Planner-Executor-Reviewer 多智能体架构 |
| 📊 EVM 挣值管理 | PV/EV/AC/CPI/SPI 全指标 + AI 预测 |
| 🔄 异步任务框架 | 大模型任务后台异步执行 + WebSocket 实时进度推送 |
| 📱 离线编辑与冲突合并 | IndexedDB 草稿箱 + 409 乐观锁解决 |
| 🔌 外部集成 | MCP / OpenClaw / Zapier / 飞书 / 企业微信 |
| 🎨 统一响应格式 | 全 API `{code, data, message}` 信封 + 中间件强制约束 |
