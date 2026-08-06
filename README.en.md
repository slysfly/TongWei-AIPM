# TongWei AI-PM (AI-Assisted Project Management System)

> An AI-assisted management platform for the full project lifecycle, aligned with the PMI framework

## 🌐 Languages
- [简体中文](README.md)
- [English](README.en.md)
- [繁體中文](README.zh-TW.md)
- [日本語](README.ja.md)
- [한국어](README.ko.md)
- [Español](README.es.md)
- [Français](README.fr.md)

## About

TongWei AI-PM is an AI-assisted platform for project management (PMI China framework). It integrates Agent workflows, knowledge-base retrieval with document preview, structured ITTO capabilities, and case-based teaching and training systems to help project managers and teams boost productivity with AI.

## Key Features

- **Agent system**: 85 domain/knowledge-unit agents with a unified 6-field schema, supporting manual and automated runs.
- **Knowledge Base (KB)**: parse, vectorize and preview multi-format documents (PDF/Word/Excel/images/text) online.
- **Structured ITTO**: turn project management inputs/tools & techniques/outputs (ITTO) into structured data for agent invocation.
- **Case teaching / training**: content for PMI certification and real-world practice.
- **PWA offline**: Service Worker caching with offline access and installable PWA.
- **Multi-language UI**: built-in i18n with Chinese/English switching.
- **Admin console**: users, permissions, knowledge base and run monitoring.

## Tech Stack

- **Frontend**: React + TypeScript + Vite + Ant Design
- **Backend**: FastAPI + PostgreSQL + pgvector (vector search)
- **Deploy**: Nginx reverse proxy, systemd service (ai-pm.service), PWA

## Deploy & Run

Frontend build:

```bash
cd frontend && npm install && npm run build
```

Backend start:

```bash
cd backend && pip install -r requirements.txt && uvicorn serve:app --host 0.0.0.0 --port 8000
```

For full deployment, operations and installation guidance, see `DEPLOYMENT.md`, `操作手册.md` and `管理员运维手册.md` in the repo.

## License

This project is released under a **Custom Commercial License**: all rights reserved. Source code is for viewing and evaluation only; any copy, modification, distribution, sublicense or commercial use requires prior written authorization from the copyright holder. Provided as-is, without warranty. See the `LICENSE` file.
