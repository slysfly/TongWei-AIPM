# AI-PM v1.1.0 安装包使用说明

本安装包为**开箱即用版**：后端（FastAPI）+ 预构建前端（React）同源托管在 **8000 端口**，
默认使用 **SQLite + 内存 Redis/Celery**，无需安装任何数据库或中间件。
只需目标机器装有 **Python 3.11+**，解压后运行启动脚本即可使用。

## 目录结构
```
通维AI-1.1.0/
├── install.sh        # 全新 Linux 一键安装器（推荐）
├── uninstall.sh      # 卸载脚本（--purge 同时清理 venv）
├── ai-pm.service     # Linux systemd 服务样例（install.sh 会自动生成更精准的单元）
├── README-安装包.md   # 本文件
├── backend/          # 后端（含 .env.example 模板，首次启动自动生成 .env）
│   └── serve.py      # 生产入口（同时托管前端）
└── frontend/         # 前端源码（含已构建的 frontend/dist，离线可用）
    └── dist/         # 已构建的前端产物（无需 node/npm 即可运行）
```

## 全新 Linux 一键部署（推荐）

将发布包拷贝到任意全新 Linux 服务器后，**一条命令完成全部部署**（自动建 venv、装依赖、初始化数据库、注册 systemd 服务、健康检查）：

```bash
# 交互式（自动生成随机密钥，管理员默认口令 admin123）
bash install.sh

# 非交互：指定管理员强口令（生产必做）
AIPM_ADMIN_PASSWORD='Str0ng#Passw0rd' bash install.sh

# 使用 PostgreSQL（提前在 backend/.env 填好 DATABASE_URL 后）
bash install.sh --pg

# 额外用 npm 重新构建前端（需 Node 18+，默认直接用包内 dist）
bash install.sh --build

# 容器/无 systemd 环境：前台或 nohup 运行
bash install.sh --no-service
```

部署完成后访问 **http://<服务器IP>:8000**，默认账号 **admin / 您设置的口令**。
卸载：`bash uninstall.sh`（加 `--purge` 同时清理 venv）。

> 默认采用 **SQLite + 内存 Redis/Celery**，零外部依赖、无需安装数据库或中间件。
> 需要 PostgreSQL 时，编辑 `backend/.env` 的 `DATABASE_URL` 后加 `--pg` 运行即可。

## 快速启动（手动，可选）
> 推荐直接用上面的 `bash install.sh` 一键部署。以下为不使用 install.sh 时的手动方式。
- **作为系统服务（手动）**: `sudo cp ai-pm.service /etc/systemd/system/ && sudo systemctl enable --now ai-pm`
  （注意：样例 `ai-pm.service` 写死了 `/opt/AI-PM/backend` 路径，请按需修改或直接使用 `install.sh` 自动生成）
- **前台 / 容器运行**: 进入 `backend/`，`python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python serve.py`

## 访问
- 管理界面: **http://localhost:8000**
- API 文档: **http://localhost:8000/docs**
- 默认账号: **admin / admin123**（已内置默认口令，首次启动即可登录；出于安全，登录后请到「系统设置 → 用户」修改密码；若要禁用默认口令，在 backend/.env 将 INITIAL_ADMIN_PASSWORD 改为强密码后重启）

## 本版本内置能力（v1.1.0）
- ✅ **Agent 手动运行对话框**：点任意 Agent「运行」→ 展示输入文件检索过程与结果 → 工具技术运用动画（慢模式逐条"执行中→完成"，快模式跳过直出）→ 最终结果以 Markdown 渲染；快/慢模式可选。
- ✅ **85 个 Agent 全覆盖**：75 个 PMBOK/CPMAI 知识单元（49 个 PMBOK6 过程 + 7 原则 + 7 绩效域 + 1 裁剪 + 7 CPMAI 阶段 + 4 可信 AI）+ 10 个领域 Agent（报告/挣值/风险/会议纪要/WBS/资源/质量/合规/健康度/决策），每个都有统一 ITTO（输入/工具技术/输出）结构。
- ✅ **ITTO 物料驱动流水线**：每项可设"选用/必需"，运行时按需检索系统物料 → AI 生成统一模板 → 工具处理 → 输出文件。
- ✅ 左侧导航栏可滚动、404 页面、OpenClaw 配置持久化、API 锁定 8000 端口。
- ✅ AI 功能需在「系统设置 → 大模型配置」填入任一厂商 API Key 后启用（不填则 AI 相关按钮优雅提示，不影响其余功能）。

## 与 OpenClaw 联动
系统自动同步大模型配置到本机 OpenClaw（`~/.openclaw/system_model.json` + HTTP 推送），
无需手动给 OpenClaw 配模型。在 Settings 页面可设置服务地址与开关（默认关闭，开启需本机有 OpenClaw 服务）。

## 可选组件：本地知识库嵌入
默认安装**不含** `sentence-transformers`（本地向量化模型，体积较大）。若要在「知识库」中使用本地嵌入（默认 `RAG_EMBEDDING_PROVIDER=local`），需额外安装：
```bash
cd backend && source venv/bin/activate
pip install sentence-transformers   # 首次使用会联网下载 BGE 权重
```
不安装也不影响系统运行——AI 对话、Agent 流程等核心功能均可用；仅本地知识库向量化不可用（可改用云端 Embedding API，或在「系统设置 → 大模型配置」填入 Embedding Key）。

## 生产建议（可选）
见 `backend/.env` 注释，切换 PostgreSQL / 设置强密码 / 关闭 memory 模式（改为真实 Redis）。

## 常见问题
- **端口 8000 被占用**: 启动前设置 `PORT=9000`
- **重置数据**: 删除 `backend/tw_ai_pms.db` 后重启
- **pip 慢**: `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

AI-PM v1.1.0 | 通维咨询AI项目管理系统
