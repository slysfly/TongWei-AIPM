# TongWei AI-PM (Sistema de gestión de proyectos asistido por IA)

> Plataforma de gestión asistida por IA para todo el ciclo de vida del proyecto, alineada con el marco PMI

## 🌐 Idiomas / Languages
- [简体中文](README.md)
- [English](README.en.md)
- [繁體中文](README.zh-TW.md)
- [日本語](README.ja.md)
- [한국어](README.ko.md)
- [Español](README.es.md)
- [Français](README.fr.md)

## Acerca de

TongWei AI-PM es una plataforma de gestión de proyectos asistida por IA (marco PMI China). Integra flujos de trabajo de agentes, recuperación de base de conocimientos con vista previa de documentos, capacidades ITTO estructuradas y sistemas de enseñanza y formación basados en casos para ayudar a los directores de proyecto y equipos a ser más productivos con IA.

## Funciones principales

- **Sistema de agentes**: 85 agentes de dominio/unidades de conocimiento integrados, con un esquema unificado de 6 campos; soporta ejecución manual y automatizada.
- **Base de conocimientos (KB)**: analiza, vectoriza y previsualiza en línea documentos de varios formatos (PDF/Word/Excel/imágenes/texto).
- **ITTO estructurado**: convierte los ITTO (entradas/herramientas y técnicas/salidas) de la gestión de proyectos en datos estructurados para su invocación por agentes.
- **Enseñanza por casos / formación**: contenidos para la certificación PMI y la práctica real.
- **PWA sin conexión**: caché de Service Worker con acceso sin conexión y PWA instalable.
- **Interfaz multilingüe**: i18n integrado con conmutación entre chino/inglés, etc.
- **Consola de administración**: usuarios, permisos, base de conocimientos y monitoreo de ejecución.

## Stack tecnológico

- **Frontend**: React + TypeScript + Vite + Ant Design
- **Backend**: FastAPI + PostgreSQL + pgvector (búsqueda vectorial)
- **Despliegue**: proxy inverso Nginx, servicio systemd (ai-pm.service), PWA

## Despliegue y ejecución

Compilación del frontend:

```bash
cd frontend && npm install && npm run build
```

Arranque del backend:

```bash
cd backend && pip install -r requirements.txt && uvicorn serve:app --host 0.0.0.0 --port 8000
```

Para una guía completa de despliegue, operación e instalación, consulte `DEPLOYMENT.md`, `操作手册.md` y `管理员运维手册.md` en el repositorio.

## Licencia

Este proyecto adopta una **licencia comercial personalizada**: todos los derechos reservados. El código fuente es solo para visualización y evaluación; cualquier copia, modificación, distribución, relicencia o uso comercial requiere autorización escrita previa del titular de los derechos. Se proporciona "tal cual", sin garantía. Véase el archivo `LICENSE`.
