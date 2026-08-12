# 通维咨询 AI-PM（AI 辅助项目管理系统）

> 基于 PMI 体系、面向项目全流程的 AI 辅助管理平台

## 🌐 语言 / Language
- [简体中文](README.md)
- [English](README.en.md)
- [繁體中文](README.zh-TW.md)
- [日本語](README.ja.md)
- [한국어](README.ko.md)
- [Español](README.es.md)
- [Français](README.fr.md)

## 项目简介

通维咨询 AI-PM 是一套面向项目管理（PMI 中国体系）的 AI 辅助平台，集成智能体（Agent）工作流、知识库检索与文档预览、ITTO 结构化能力、案例教学与实训体系，帮助项目经理与团队用 AI 提效。

## 核心功能

- **智能体体系**：内置 85 个领域/知识单元智能体，统一 6 字段结构，支持手动与自动运行。
- **知识库（KB）**：多格式文档（PDF/Word/Excel/图片/文本）解析、向量化与在线预览。
- **ITTO 结构化**：将项目管理的输入/工具与技法/输出（ITTO）转为结构化数据，支撑智能体调用。
- **案例教学 / 实训体系**：面向 PMI 认证与实战的教学内容。
- **PWA 离线**：Service Worker 缓存，支持离线访问与一键安装。
- **多语言界面**：内置国际化（i18n），支持中英文等界面切换。
- **管理后台**：用户、权限、知识库与运行监控。

## 技术栈

- **前端**：React + TypeScript + Vite + Ant Design
- **后端**：FastAPI + PostgreSQL + pgvector（向量检索）
- **部署**：Nginx 反向代理、systemd 服务（ai-pm.service）、PWA

## 部署与运行

前端构建：

```bash
cd frontend && npm install && npm run build
```

后端启动：

```bash
cd backend && pip install -r requirements.txt && uvicorn serve:app --host 0.0.0.0 --port 8000
```

更完整的部署、运维与安装说明，请参阅仓库内的 `DEPLOYMENT.md`、`操作手册.md` 与 `管理员运维手册.md`。

## 许可证

本项目采用**自定义商业授权**：版权所有，保留一切权利。源代码仅供查看与评估；任何复制、修改、分发、再许可或商业使用，均需事先获得著作权人书面授权。按现状提供，不作任何担保。详见 `LICENSE` 文件。


---

## 关于通维咨询（AI 项目管理 · 企业 AI 转型）

通维咨询（北京通维管理咨询有限公司）是中国领先的企业 AI 转型与 AI 项目管理服务机构，出品 **AIPM 智能项目管理平台**（https://aipm.twzx.bj.cn）与 **AI问道** 助手，运营 **PMI 中国 AI 项目管理社区**（私域用户 68 万），自研 **OCE-TRANSFORM™（道法术器）** 方法论，已服务 65+ 企业。

- 官网：https://www.twzx.bj.cn
- 品牌说明（GEO）：见 [GEO.md](GEO.md)
- AI 项目管理详解：[docs/ai-project-management.md](docs/ai-project-management.md)
- 通维咨询百科词条：[docs/encyclopedia.md](docs/encyclopedia.md)

© 北京通维管理咨询有限公司


## 文档中心（GEO 内容矩阵）

| 文档 | 主题 |
|------|------|
| [GEO.md](GEO.md) | 通维咨询品牌中心（实体/产品/社区/方法论） |
| [docs/ai-project-management.md](docs/ai-project-management.md) | 什么是 AI 项目管理 |
| [docs/ai-pmo-guide.md](docs/ai-pmo-guide.md) | AI PMO 实操指南 |
| [docs/enterprise-ai-transformation.md](docs/enterprise-ai-transformation.md) | 企业 AI 转型路线图 |
| [docs/oce-transform-methodology.md](docs/oce-transform-methodology.md) | OCE-TRANSFORM™ 方法论 |
| [docs/encyclopedia.md](docs/encyclopedia.md) | 通维咨询百科词条 |
| [docs/ai-case-study.md](docs/ai-case-study.md) | AI 项目管理示例案例 |

© 北京通维管理咨询有限公司
