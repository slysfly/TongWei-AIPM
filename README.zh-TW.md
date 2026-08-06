# 通維 AI-PM（AI 輔助專案管理系統）

> 基於 PMI 體系、面向專案全流程的 AI 輔助管理平台

## 🌐 語言 / Language
- [简体中文](README.md)
- [English](README.en.md)
- [繁體中文](README.zh-TW.md)
- [日本語](README.ja.md)
- [한국어](README.ko.md)
- [Español](README.es.md)
- [Français](README.fr.md)

## 專案簡介

通維 AI-PM 是一套面向專案管理（PMI 中國體系）的 AI 輔助平台，整合智慧體（Agent）工作流程、知識庫檢索與文件預覽、ITTO 結構化能力、案例教學與實訓體系，協助專案經理與團隊以 AI 提升效率。

## 核心功能

- **智慧體體系**：內建 85 個領域/知識單元智慧體，統一 6 欄位結構，支援手動與自動執行。
- **知識庫（KB）**：多格式文件（PDF/Word/Excel/圖片/文字）解析、向量化與線上預覽。
- **ITTO 結構化**：將專案管理的輸入/工具與技法/輸出（ITTO）轉為結構化資料，支撐智慧體呼叫。
- **案例教學 / 實訓體系**：面向 PMI 認證與實戰的教學內容。
- **PWA 離線**：Service Worker 快取，支援離線存取與一鍵安裝。
- **多語系介面**：內建國際化（i18n），支援中英文等介面切換。
- **管理後台**：使用者、權限、知識庫與執行監控。

## 技術堆疊

- **前端**：React + TypeScript + Vite + Ant Design
- **後端**：FastAPI + PostgreSQL + pgvector（向量檢索）
- **部署**：Nginx 反向代理、systemd 服務（ai-pm.service）、PWA

## 部署與執行

前端建置：

```bash
cd frontend && npm install && npm run build
```

後端啟動：

```bash
cd backend && pip install -r requirements.txt && uvicorn serve:app --host 0.0.0.0 --port 8000
```

更完整的部署、運維與安裝說明，請參閱倉庫內的 `DEPLOYMENT.md`、`操作手册.md` 與 `管理员运维手册.md`。

## 授權條款

本專案採**自訂商業授權**：版權所有，保留一切權利。原始碼僅供檢視與評估；任何複製、修改、散佈、再授權或商業使用，均須事先取得著作權人書面授權。依現狀提供，不負任何擔保。詳見 `LICENSE` 檔案。
