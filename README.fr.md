# TongWei AI-PM (Système de gestion de projet assisté par IA)

> Plateforme de gestion assistée par IA pour l'ensemble du cycle de vie du projet, alignée sur le référentiel PMI

## 🌐 Langues / Languages
- [简体中文](README.md)
- [English](README.en.md)
- [繁體中文](README.zh-TW.md)
- [日本語](README.ja.md)
- [한국어](README.ko.md)
- [Español](README.es.md)
- [Français](README.fr.md)

## À propos

TongWei AI-PM est une plateforme de gestion de projets assistée par IA (référentiel PMI Chine). Elle intègre des flux de travail d'agents, la recherche dans une base de connaissances avec aperçu des documents, des capacités ITTO structurées et des systèmes d'enseignement et de formation basés sur des cas pour aider les chefs de projet et les équipes à gagner en productivité grâce à l'IA.

## Fonctionnalités clés

- **Système d'agents** : 85 agents de domaine/unités de connaissances intégrés, avec un schéma unifié de 6 champs ; exécution manuelle et automatisée prise en charge.
- **Base de connaissances (KB)** : analyse, vectorise et prévisualise en ligne des documents de plusieurs formats (PDF/Word/Excel/images/texte).
- **ITTO structuré** : convertit les ITTO (entrées/outils et techniques/sorties) de la gestion de projet en données structurées pour invocation par les agents.
- **Enseignement par cas / formation** : contenus pour la certification PMI et la pratique réelle.
- **PWA hors ligne** : cache Service Worker avec accès hors ligne et PWA installable.
- **Interface multilingue** : i18n intégré avec bascule chinois/anglais, etc.
- **Console d'administration** : utilisateurs, permissions, base de connaissances et supervision d'exécution.

## Stack technique

- **Frontend** : React + TypeScript + Vite + Ant Design
- **Backend** : FastAPI + PostgreSQL + pgvector (recherche vectorielle)
- **Déploiement** : proxy inverse Nginx, service systemd (ai-pm.service), PWA

## Déploiement et exécution

Build du frontend :

```bash
cd frontend && npm install && npm run build
```

Démarrage du backend :

```bash
cd backend && pip install -r requirements.txt && uvicorn serve:app --host 0.0.0.0 --port 8000
```

Pour un guide complet de déploiement, d'exploitation et d'installation, voir `DEPLOYMENT.md`, `操作手册.md` et `管理员运维手册.md` dans le dépôt.

## Licence

Ce projet adopte une **licence commerciale personnalisée** : tous droits réservés. Le code source est fourni uniquement pour consultation et évaluation ; toute copie, modification, distribution, reclicence ou usage commercial nécessite une autorisation écrite préalable du titulaire des droits. Fourni « en l'état », sans garantie. Voir le fichier `LICENSE`.
