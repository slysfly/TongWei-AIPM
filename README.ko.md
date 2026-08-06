# 통웨이 AI-PM (AI 지원 프로젝트 관리 시스템)

> PMI 프레임워크에 부합하는 전(全) 프로젝트 생애주기용 AI 지원 관리 플랫폼

## 🌐 언어 / Languages
- [简体中文](README.md)
- [English](README.en.md)
- [繁體中文](README.zh-TW.md)
- [日本語](README.ja.md)
- [한국어](README.ko.md)
- [Español](README.es.md)
- [Français](README.fr.md)

## 소개

통웨이 AI-PM은 프로젝트 관리(PMI 중국 프레임워크)를 위한 AI 지원 플랫폼입니다. 에이전트 워크플로, 지식베이스 검색 및 문서 미리보기, 구조화된 ITTO 기능, 사례 기반 교육 및 실습 체계를 통합하여 프로젝트 매니저와 팀의 생산성을 AI로 향상시킵니다.

## 핵심 기능

- **에이전트 체계**: 도메인/지식 단위 에이전트 85개 내장, 통일된 6필드 스키마, 수동·자동 실행 지원.
- **지식베이스(KB)**: PDF/Word/Excel/이미지/텍스트 등 다양한 형식 문서를 파싱·벡터화하고 온라인 미리보기.
- **구조화 ITTO**: 프로젝트 관리의 ITTO(입력/도구와 기법/산출물)를 구조화 데이터로 변환하여 에이전트 호출 가능.
- **사례 교육 / 실습 체계**: PMI 인증 및 실무용 콘텐츠.
- **PWA 오프라인**: Service Worker 캐싱으로 오프라인 접속 및 설치형 PWA 지원.
- **다국어 UI**: 내장 i18n으로 중국어/영어 등 전환.
- **관리 콘솔**: 사용자, 권한, 지식베이스, 실행 모니터링.

## 기술 스택

- **프론트엔드**: React + TypeScript + Vite + Ant Design
- **백엔드**: FastAPI + PostgreSQL + pgvector(벡터 검색)
- **배포**: Nginx 리버스 프록시, systemd 서비스(ai-pm.service), PWA

## 배포 및 실행

프론트엔드 빌드：

```bash
cd frontend && npm install && npm run build
```

백엔드 시작：

```bash
cd backend && pip install -r requirements.txt && uvicorn serve:app --host 0.0.0.0 --port 8000
```

보다 자세한 배포·운영·설치 안내는 저장소의 `DEPLOYMENT.md`, `操作手册.md`, `管理员运维手册.md`를 참고하세요.

## 라이선스

본 프로젝트는 **커스텀 상용 라이선스**를 채택하며 모든 권리를 보유합니다. 소스 코드는 열람 및 평가 목적으로만 제공됩니다.복제, 수정, 배포, 재라이선스, 상업적 사용은 사전 서면 승인이 필요합니다. 있는 그대로 제공되며 어떠한 보증도 하지 않습니다.자세한 내용은 `LICENSE` 파일을 참조하세요.
