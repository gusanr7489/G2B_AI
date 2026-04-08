# G2B_AI 프로젝트 — Claude Code 규칙

## 프로젝트 개요
나라장터 용역 공고(IT 컨설팅) AI 분석 플랫폼.
공고 자동 수집 → HWP 변환 → AI 분석(RFP 핵심 추출) → 제안목차 자동 생성 → 담당자/CEO 대시보드.

## 기술 스택
- **백엔드**: Python 3.11+, FastAPI, PostgreSQL + pgvector, httpx
- **프론트엔드**: React 19, TypeScript, Vite, Ant Design, TanStack Query
- **AI**: Google Gemini API
- **HWP 변환**: 리브레AI API (1순위), 로컬 라이브러리 (2순위)
- **인증**: JWT 기반 로그인
- **알림**: 이메일/슬랙 연동

## 실행 방법

### 백엔드
```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
```

### 프론트엔드
```bash
cd frontend && npm run dev
```

## 개발 규칙

### 공통
- 커밋 메시지는 **한글** 1줄, 50자 이내
- `.env` 파일은 절대 커밋하지 않음

### 백엔드 수정 시
- async/await 패턴 일관 사용
- PostgreSQL + asyncpg 사용 (SQLite 아님)
- 라우터: `routers/`에 APIRouter로 분리, main.py에서 등록
- 서비스: `services/`에 비즈니스 로직 분리
- Pydantic 스키마: `schemas/`에 정의
- 에러: HTTPException 사용

### 프론트엔드 수정 시
- TypeScript strict mode
- Ant Design 컴포넌트 우선 사용
- @tanstack/react-query로 서버 상태 관리

### 조달청 API 관련
- 날짜 파라미터: **YYYYMMDDHHmm** (12자리) 형식 필수
- serviceKey는 URL 인코딩된 상태로 전달
