# G2B_AI 구현 워크플로우

## Phase 1: 프로젝트 기반 셋업 (1주)

### 1-1. 백엔드 초기화
- [ ] `backend/` 디렉토리 생성
- [ ] Python venv 생성, `requirements.txt` 작성
  - fastapi, uvicorn, asyncpg, httpx, python-jose, passlib, bcrypt, apscheduler, python-dotenv
- [ ] `main.py` — FastAPI 앱, CORS, 라우터 등록
- [ ] `config.py` — 환경변수 로딩 (pydantic-settings)
- [ ] `database.py` — asyncpg 연결 풀
- [ ] `.env` 템플릿 생성 (`.env.example`)

**검증**: `uvicorn main:app --reload` → `/docs` Swagger UI 확인

### 1-2. 데이터베이스
- [ ] `docker-compose.yml` — PostgreSQL 15 컨테이너
- [ ] `models/tables.sql` — DDL 스크립트 (ARCHITECTURE.md 섹션 4 기준)
  - users, bids, bid_attachments, analyses, proposal_outlines, bid_targets
- [ ] 초기 admin 계정 seed 스크립트

**검증**: `psql` 접속 → 테이블 6개 생성 확인

### 1-3. 인증 시스템
- [ ] `schemas/auth.py` — LoginRequest, TokenResponse, UserCreate, UserResponse
- [ ] `services/auth_service.py` — JWT 발급/검증, bcrypt 해싱
- [ ] `routers/auth.py` — POST `/login`, POST `/invite`, GET `/me`
- [ ] JWT 미들웨어 (dependencies)
- [ ] 역할 검증 데코레이터 (`require_admin`)

**검증**: Swagger에서 로그인 → 토큰 발급 → `/me` 호출 성공

### 1-4. 프론트엔드 초기화
- [ ] `npm create vite@latest frontend -- --template react-ts`
- [ ] Ant Design, TanStack Query, axios, react-router-dom 설치
- [ ] `api/client.ts` — axios 인스턴스 (JWT 인터셉터)
- [ ] `App.tsx` — 라우팅 설정 (`/login`, `/dashboard`, `/ceo`, `/bids/:id`)
- [ ] `pages/LoginPage.tsx` — 로그인 폼
- [ ] `hooks/useAuth.ts` — 인증 상태 관리

**검증**: 로그인 → 대시보드 리다이렉트 동작

---

## Phase 2: 공고 수집 (1주)

### 2-1. 나라장터 API 연동
- [ ] `services/g2b_service.py`
  - `search_bids(params)` — 용역 공고 목록 조회
  - `get_bid_detail(bid_ntce_no)` — 공고 상세 + 첨부파일 URL
  - 날짜 포맷: YYYYMMDDHHmm (12자리) 준수
  - serviceKey URL 인코딩 처리
  - 재시도 로직 (3회, exponential backoff)
- [ ] `schemas/bid.py` — BidListResponse, BidDetail, BidSearchParams
- [ ] `routers/bids.py`
  - GET `/api/bids` — DB에서 수집된 목록 조회 (페이지네이션, 필터)
  - GET `/api/bids/{id}` — 공고 상세
  - POST `/api/bids/search` — 나라장터 수동 검색
  - POST `/api/bids/{id}/collect` — 특정 공고 수집 트리거

**검증**: `/api/bids/search` 호출 → 나라장터 응답 → DB 저장 확인

### 2-2. 자동 수집 스케줄러
- [ ] `services/scheduler_service.py`
  - APScheduler CronTrigger: 10:00, 14:00, 20:00
  - 수집 작업: 최근 N시간 신규 공고 조회 → 중복 필터 → DB 저장
  - 실패 로깅 + 다음 스케줄에 재시도
- [ ] `main.py`에 스케줄러 startup/shutdown 이벤트 등록

**검증**: 스케줄러 수동 트리거 → 공고 수집 → DB 확인

### 2-3. 프론트엔드 — 공고 목록
- [ ] `api/bids.ts` — API 클라이언트 함수
- [ ] `components/BidListPanel.tsx` — 공고 리스트 (Ant Design Table)
  - 검색/필터, 페이지네이션
  - 공고명, 발주기관, 마감일, 예산 표시
- [ ] `pages/StaffDashboard.tsx` — 좌측 현황 리스트 패널 배치

**검증**: 대시보드에서 수집된 공고 목록 표시

---

## Phase 3: HWP 변환 + AI 분석 (1~2주)

### 3-1. HWP 변환 서비스
- [ ] `services/hwp_service.py`
  - `convert_hwp(file_bytes)` → HTML + MD 텍스트 반환
  - 리브레AI API 비동기 플로우: 업로드 → 폴링 → ZIP 다운로드 → 추출
  - 일일 50회 한도 카운트 (DB 또는 Redis)
  - 실패 시 `conversion_status = 'failed'`
- [ ] 공고 수집 파이프라인에 HWP 변환 연결
  - 첨부파일 URL → 다운로드 → HWP면 변환, PDF면 텍스트 추출
  - `bid_attachments` 테이블에 결과 저장

**검증**: HWP 파일 업로드 → HTML/MD 변환 → DB 저장 확인

### 3-2. Gemini AI 분석 서비스
- [ ] `services/analysis_service.py`
  - `analyze_rfp(bid_id)` — 첨부파일 텍스트 로드 → Gemini 호출 → 파싱 → 저장
  - JSON 출력 스키마 강제 (response_mime_type: application/json)
  - 독소조항 탐지 로직 포함 (31개 체크항목)
  - 타임아웃 60초, 재시도 2회
- [ ] `prompts/rfp_analysis.py` — 프롬프트 템플릿
  - 시스템 프롬프트: 공공 IT 컨설팅 RFP 분석 전문가
  - 추출 항목: 기본정보, 평가기준, 요구사항, 참가자격, 기술요구, 독소조항
  - 독소조항 체크리스트 (docs/poison_clauses_research.md 기반)
  - 출력 JSON 스키마 명시
- [ ] `schemas/analysis.py` — AnalysisResponse, PoisonClause, RiskLevel
- [ ] `routers/analyses.py`
  - POST `/api/analyses/{bid_id}` — 분석 요청 (비동기)
  - GET `/api/analyses/{bid_id}` — 결과 조회
  - GET `/api/analyses/{bid_id}/status` — 상태 확인

**검증**: 수집된 공고 → AI 분석 요청 → 구조화된 JSON 결과 + 독소조항 확인

### 3-3. 제안목차 생성 (수동)
- [ ] `prompts/outline_generation.py` — 목차 생성 프롬프트
  - ISP/ISMP 판별 → 해당 가이드라인 기반 목차 구조
  - 평가항목 배점 반영
  - L1~L4 계층 JSON 출력
- [ ] `routers/analyses.py`에 추가
  - POST `/api/analyses/{bid_id}/outline` — 목차 생성 (수동 트리거)
  - GET `/api/analyses/{bid_id}/outline` — 목차 조회

**검증**: 분석 완료된 공고 → 목차 생성 클릭 → L1~L4 트리 JSON 확인

---

## Phase 4: 대시보드 UI (1주)

### 4-1. 담당자 대시보드
- [ ] `pages/StaffDashboard.tsx` — 2패널 레이아웃 완성
  - 좌측: 현황 리스트 (BidListPanel)
  - 우측: 대상 리스트 (TargetListPanel)
  - `→` 버튼: 공고를 대상으로 이동
- [ ] `components/TargetListPanel.tsx`
  - 상태 필터 (검토필요/검토중/진행중/완료)
  - 독소조항 위험도 배지 표시
  - 인라인 수정: 필요인원, 사무실, 비용, 견적
- [ ] `api/targets.ts` — 대상 관리 API 클라이언트
- [ ] `routers/targets.py`
  - POST/GET/PATCH/DELETE `/api/targets`

**검증**: 공고 선택 → 대상 이동 → 상태 변경 → 정보 입력

### 4-2. 공고 상세 페이지
- [ ] `pages/BidDetail.tsx` — 탭 기반 상세 뷰
  - 기본 정보 헤더 (공고명, 기관, 마감일, 위험도 배지)
  - [AI 분석 요청] 버튼, [목차 생성] 버튼
  - 탭: AI 분석 / 독소조항 / 첨부파일 / 제안목차
- [ ] `components/AnalysisView.tsx` — 분석 결과 렌더링
  - 사업개요, 범위, 평가항목 테이블, 요구사항 목록
- [ ] `components/PoisonClauseView.tsx` — 독소조항 뷰
  - 종합 위험도, 항목별 테이블 (카테고리/조항/심각도/사유)
- [ ] `components/OutlineView.tsx` — 목차 트리 뷰
  - Ant Design Tree 컴포넌트
  - [PDF 내보내기] 버튼 (후순위)

**검증**: 공고 클릭 → 분석 요청 → 결과 탭별 확인 → 독소조항 배지

### 4-3. CEO 대시보드
- [ ] `pages/CeoDashboard.tsx`
  - 현황 요약 카드 (상태별 건수)
  - 대상 리스트 테이블 (담당자, 인원, 비용, 견적, 마감일)
  - 마감 임박 알림 (D-7 이내)
- [ ] `routers/dashboard.py`
  - GET `/api/dashboard/stats` — 상태별 집계, 마감 임박 목록
  - GET `/api/dashboard/my` — 내 담당 현황
- [ ] `components/StatsCard.tsx` — 통계 카드 컴포넌트

**검증**: CEO 로그인 → 전체 현황 통계 + 대상 리스트 + 마감 임박

---

## Phase 5: 고도화 (MVP 이후)

### 5-1. 알림 시스템
- [ ] 슬랙 웹훅 연동
- [ ] 이메일 발송 (SMTP/SendGrid)
- [ ] 신규 공고 수집 시 알림 트리거

### 5-2. 유사 공고 검색
- [ ] pgvector 확장 설치
- [ ] Gemini 임베딩 모델 (text-embedding-004) 연동
- [ ] 공고 텍스트 벡터화 → 유사도 검색 API

### 5-3. 제안목차 고도화
- [ ] 하네스 엔지니어링으로 프롬프트 최적화
- [ ] 기업 실제 제안서 목차 샘플 학습
- [ ] Excel 내보내기

---

## 의존성 맵

```
Phase 1-1 (백엔드) ──┐
Phase 1-2 (DB)     ──┼── Phase 1-3 (인증) ── Phase 2-1 (나라장터)
Phase 1-4 (프론트) ──┘                       │
                                              ├── Phase 2-2 (스케줄러)
                                              │
                                              └── Phase 3-1 (HWP) ──┐
                                                                     ├── Phase 3-2 (AI 분석)
                                                                     │        │
                                                                     │        └── Phase 3-3 (목차)
                                                                     │
                                              Phase 2-3 (목록 UI) ───┴── Phase 4-1 (대시보드)
                                                                              │
                                                                     Phase 4-2 (상세)
                                                                              │
                                                                     Phase 4-3 (CEO)
```

## 체크포인트

| 시점 | 검증 내용 | 통과 기준 |
|------|---------|----------|
| Phase 1 완료 | 로그인 → JWT → /me | 토큰 기반 인증 동작 |
| Phase 2 완료 | 나라장터 검색 → DB 저장 → 목록 표시 | 실제 공고 10건 이상 수집 |
| Phase 3 완료 | HWP 변환 → AI 분석 → 독소조항 탐지 | 샘플 RFP 3건 분석 성공 |
| Phase 4 완료 | 담당자 워크플로우 E2E | 수집→선별→분석→상태관리 전체 흐름 |
| MVP 완료 | CEO 대시보드 + 전체 통합 | 데모 시나리오 1회 완주 |
