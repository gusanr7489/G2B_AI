# G2B_AI 시스템 아키텍처

## 1. 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React 19)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  로그인 페이지  │  │ 담당자 대시보드 │  │    CEO 대시보드        │ │
│  └──────────────┘  │ ┌────┐┌────┐ │  │  대상 리스트 + 통계     │ │
│                     │ │현황││대상│ │  └────────────────────────┘ │
│                     │ └────┘└────┘ │                             │
│                     └──────────────┘                             │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │              공고 상세 / AI 분석 결과 뷰                      ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (REST API)
┌──────────────────────────▼──────────────────────────────────────┐
│                     Backend (FastAPI)                             │
│                                                                   │
│  ┌─────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Auth   │  │  Bid Router  │  │ Analysis │  │  Dashboard   │  │
│  │ Router  │  │ (공고 CRUD)  │  │  Router  │  │   Router     │  │
│  └────┬────┘  └──────┬──────┘  └─────┬────┘  └──────┬───────┘  │
│       │              │               │               │           │
│  ┌────▼────┐  ┌──────▼──────┐  ┌─────▼────┐  ┌──────▼───────┐  │
│  │  Auth   │  │    G2B      │  │ Analysis │  │  Dashboard   │  │
│  │ Service │  │  Service    │  │  Service │  │   Service    │  │
│  └─────────┘  └──────┬──────┘  └─────┬────┘  └──────────────┘  │
│                      │               │                           │
│               ┌──────▼──────┐  ┌─────▼─────────┐               │
│               │  HWP Conv.  │  │  Gemini AI    │               │
│               │  Service    │  │  Service      │               │
│               └──────┬──────┘  └───────────────┘               │
│                      │                                           │
│  ┌───────────────────┼──────────────────────────┐               │
│  │            Scheduler (APScheduler)            │               │
│  │  - 공고 자동 수집 (10:00 / 14:00 / 20:00)     │               │
│  │  - HWP 변환 큐 처리                            │               │
│  └───────────────────────────────────────────────┘               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌────────────┐  ┌────────────┐  ┌──────────────┐
   │ PostgreSQL │  │ 나라장터    │  │  리브레AI     │
   │            │  │ Open API   │  │  API          │
   │ - users    │  │            │  │              │
   │ - bids     │  │ 공고 수집   │  │ HWP→HTML+MD │
   │ - analyses │  └────────────┘  └──────────────┘
   │ - targets  │
   └────────────┘         ┌──────────────┐
                          │  Google       │
                          │  Gemini API   │
                          │              │
                          │ RFP 분석     │
                          └──────────────┘
```

---

## 2. 디렉토리 구조

```
G2B_AI/
├── backend/
│   ├── main.py                    # FastAPI 앱 진입점
│   ├── config.py                  # 환경변수, 설정
│   ├── database.py                # DB 연결 (asyncpg)
│   │
│   ├── routers/                   # API 라우터
│   │   ├── auth.py                # 로그인/토큰 발급
│   │   ├── bids.py                # 공고 CRUD, 수동 검색
│   │   ├── analyses.py            # AI 분석 요청/결과
│   │   ├── targets.py             # 대상 리스트 관리
│   │   └── dashboard.py           # 대시보드 통계
│   │
│   ├── services/                  # 비즈니스 로직
│   │   ├── auth_service.py        # JWT, 비밀번호 해싱
│   │   ├── g2b_service.py         # 나라장터 API 연동
│   │   ├── hwp_service.py         # 리브레AI HWP 변환
│   │   ├── analysis_service.py    # Gemini AI 분석
│   │   └── scheduler_service.py   # 자동 수집 스케줄러
│   │
│   ├── schemas/                   # Pydantic 모델
│   │   ├── auth.py
│   │   ├── bid.py
│   │   ├── analysis.py
│   │   └── target.py
│   │
│   ├── models/                    # SQLAlchemy 모델 (or raw SQL)
│   │   └── tables.sql             # DDL
│   │
│   ├── prompts/                   # Gemini 프롬프트 템플릿
│   │   ├── rfp_analysis.py        # RFP 분석 프롬프트
│   │   └── outline_generation.py  # 목차 생성 프롬프트 (후순위)
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                   # API 클라이언트
│   │   │   ├── client.ts          # axios 인스턴스
│   │   │   ├── auth.ts
│   │   │   ├── bids.ts
│   │   │   └── analyses.ts
│   │   │
│   │   ├── pages/                 # 페이지 컴포넌트
│   │   │   ├── LoginPage.tsx
│   │   │   ├── StaffDashboard.tsx # 담당자 대시보드
│   │   │   ├── CeoDashboard.tsx   # CEO 대시보드
│   │   │   └── BidDetail.tsx      # 공고 상세 + AI 분석
│   │   │
│   │   ├── components/            # 재사용 컴포넌트
│   │   │   ├── BidListPanel.tsx   # 공고 리스트 패널
│   │   │   ├── TargetListPanel.tsx# 대상 리스트 패널
│   │   │   ├── AnalysisView.tsx   # AI 분석 결과 뷰
│   │   │   └── StatsCard.tsx      # 통계 카드
│   │   │
│   │   ├── hooks/                 # 커스텀 훅
│   │   │   └── useAuth.ts
│   │   │
│   │   └── types/                 # TypeScript 타입
│   │       └── index.ts
│   │
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── CLAUDE.md
├── REQUIREMENTS.md
├── ARCHITECTURE.md
└── docker-compose.yml             # PostgreSQL + 앱
```

---

## 3. API 설계

### 3-1. 인증

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/auth/login` | 로그인 → JWT 발급 |
| POST | `/api/auth/invite` | 사용자 초대 (admin only) |
| GET | `/api/auth/me` | 현재 사용자 정보 |

### 3-2. 공고 관리

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/bids` | 수집된 공고 목록 (페이지네이션, 필터) |
| GET | `/api/bids/{id}` | 공고 상세 |
| POST | `/api/bids/search` | 나라장터 수동 검색 |
| POST | `/api/bids/{id}/collect` | 특정 공고 수집 (첨부파일 포함) |

### 3-3. AI 분석

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/analyses/{bid_id}` | AI 분석 요청 (RFP 핵심 추출 + 독소조항 탐지) |
| GET | `/api/analyses/{bid_id}` | 분석 결과 조회 |
| GET | `/api/analyses/{bid_id}/status` | 분석 진행 상태 |
| POST | `/api/analyses/{bid_id}/outline` | 제안목차 생성 (수동 트리거, LLM 비용 절감) |
| GET | `/api/analyses/{bid_id}/outline` | 생성된 제안목차 조회 |

### 3-4. 대상 관리

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/targets` | 공고를 대상 리스트로 이동 |
| GET | `/api/targets` | 대상 리스트 조회 |
| PATCH | `/api/targets/{id}` | 상태/메모/인원 등 수정 |
| DELETE | `/api/targets/{id}` | 대상에서 제거 |

### 3-5. 대시보드

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/dashboard/stats` | 전체 통계 (CEO용) |
| GET | `/api/dashboard/my` | 내 담당 현황 (담당자용) |

---

## 4. 데이터베이스 스키마 (확정)

```sql
-- 사용자
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'staff',  -- staff / admin
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 수집된 공고
CREATE TABLE bids (
    id SERIAL PRIMARY KEY,
    bid_ntce_no VARCHAR(50) NOT NULL,           -- 공고번호
    bid_ntce_ord VARCHAR(10),                   -- 공고차수
    bid_ntce_nm TEXT NOT NULL,                  -- 공고명
    ntce_instt_nm VARCHAR(200),                 -- 공고기관 (조달청 등)
    dminstt_nm VARCHAR(200),                    -- 수요기관 (실제 발주처)
    bid_close_dt TIMESTAMP,                     -- 입찰마감일시
    asign_bdgt_amt BIGINT,                      -- 배정예산
    presmpt_prce BIGINT,                        -- 추정가격
    bid_ntce_url TEXT,                          -- 공고 상세 URL
    raw_data JSONB,                             -- 나라장터 API 원본
    status VARCHAR(20) DEFAULT 'new',           -- new / processing / completed / failed
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(bid_ntce_no, bid_ntce_ord)
);

-- 공고 첨부파일
CREATE TABLE bid_attachments (
    id SERIAL PRIMARY KEY,
    bid_id INTEGER REFERENCES bids(id) ON DELETE CASCADE,
    file_name VARCHAR(500),                     -- 원본 파일명
    file_type VARCHAR(20),                      -- hwp / pdf / etc
    file_url TEXT,                              -- 나라장터 다운로드 URL
    converted_html TEXT,                        -- 변환된 HTML
    converted_md TEXT,                          -- 변환된 마크다운
    conversion_status VARCHAR(20) DEFAULT 'pending',  -- pending / completed / failed
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI 분석 결과
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    bid_id INTEGER REFERENCES bids(id) ON DELETE CASCADE,
    issuing_org VARCHAR(200),                   -- 발주기관 (추출)
    deadline TIMESTAMP,                         -- 마감일시 (추출)
    project_summary TEXT,                       -- 사업 개요
    project_scope TEXT,                         -- 사업 범위
    eval_criteria JSONB,                        -- 평가항목/배점
    requirements JSONB,                         -- 세부과업 목록
    qualification TEXT,                         -- 참가 자격 요건
    tech_requirements JSONB,                    -- 기술 요구사항
    poison_clauses JSONB,                       -- 독소조항 탐지 결과
    risk_level VARCHAR(20),                     -- 종합 위험도: safe / caution / warning / danger
    raw_analysis JSONB,                         -- AI 원본 응답
    analysis_status VARCHAR(20) DEFAULT 'pending',  -- pending / completed / failed
    created_at TIMESTAMP DEFAULT NOW()
);

-- 제안목차 (수동 생성, LLM 비용 절감)
CREATE TABLE proposal_outlines (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    outline_data JSONB NOT NULL,                -- L1~L4 계층 구조 목차
    is_ismp BOOLEAN DEFAULT false,              -- ISMP 사업 여부
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 대상 리스트
CREATE TABLE bid_targets (
    id SERIAL PRIMARY KEY,
    bid_id INTEGER REFERENCES bids(id) ON DELETE CASCADE,
    assignee_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT '검토필요',       -- 검토필요 / 검토중 / 진행중 / 완료
    required_staff INTEGER,                     -- 필요 인원
    office_info VARCHAR(200),                   -- 사무실
    estimated_cost BIGINT,                      -- 소요비용
    bid_estimate BIGINT,                        -- 사업견적
    notes TEXT,                                 -- 메모
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(bid_id)
);
```

---

## 5. 핵심 데이터 플로우

### 5-1. 공고 자동 수집 파이프라인

```
[Scheduler: 매일 10:00 / 14:00 / 20:00]
       │
       ▼
 나라장터 API 호출
 (용역공고, IT컨설팅 키워드)
       │
       ▼
 신규 공고 필터링
 (기존 DB와 공고번호 비교)
       │
       ▼
 bids 테이블 저장
 (status: new)
       │
       ▼
 첨부파일 URL 추출
       │
       ▼
 HWP 파일 다운로드
       │
       ▼
 리브레AI API 변환
 (HWP → HTML + MD)
       │
       ▼
 bid_attachments 저장
 (converted_html, converted_md)
       │
       ▼
 bids.status → 'completed'
```

### 5-2. AI 분석 플로우

```
[담당자: 분석 요청 클릭]
       │
       ▼
 bid_attachments에서
 HTML/MD 텍스트 로드
       │
       ▼
 Gemini API 호출
 (RFP 분석 프롬프트 + 텍스트)
       │
       ▼
 구조화된 JSON 응답 파싱
 ┌─────────────────────────┐
 │ 기본 분석                │
 │ - 발주기관, 마감일        │
 │ - 사업개요, 범위          │
 │ - 평가항목/배점           │
 │ - 참가자격, 요구사항      │
 ├─────────────────────────┤
 │ 독소조항 탐지             │
 │ - 평가기준 독소 (6항목)   │
 │ - 참가자격 독소 (5항목)   │
 │ - 계약조건 독소 (5항목)   │
 │ - 과업범위 독소 (5항목)   │
 │ - 인력요건 독소 (5항목)   │
 │ - 보안요건 독소 (5항목)   │
 │ → 종합 위험도 판정        │
 │   (safe/caution/warning/ │
 │    danger)               │
 └─────────────────────────┘
       │
       ▼
 analyses 테이블 저장
 (poison_clauses, risk_level)
       │
       ▼
 프론트엔드에 결과 표시
 (독소조항 경고 배지 포함)
```

### 5-3. 제안목차 생성 플로우 (수동 트리거)

```
[담당자: "목차 생성" 버튼 클릭]
       │
       ▼
 analyses에서 분석 결과 로드
 (평가항목, 요구사항, ISP/ISMP 판별)
       │
       ▼
 Gemini API 호출
 (목차 생성 프롬프트 + 분석 결과)
 ※ 별도 LLM 호출 (비용 절감 위해 자동 X)
       │
       ▼
 L1~L4 계층 구조 목차 JSON 생성
 - ISP: 환경분석→현황→목표모델→이행계획
 - ISMP: 착수→방향성→요건→구조정의→이행
 - 평가항목 배점 반영
       │
       ▼
 proposal_outlines 테이블 저장
       │
       ▼
 프론트엔드에 목차 트리 표시
```

---

## 6. 외부 API 연동 상세

### 6-1. 나라장터 Open API

```python
# 용역 공고 목록 조회
GET https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc

# 주요 파라미터
params = {
    "serviceKey": "URL_ENCODED_KEY",     # 공공데이터포털 키
    "pageNo": 1,
    "numOfRows": 100,
    "inqryDiv": 1,                       # 1:등록일시
    "inqryBgnDt": "202604080000",        # 12자리 YYYYMMDDHHmm
    "inqryEndDt": "202604081200",
    "type": "json"
}
```

### 6-2. 리브레AI HWP 변환 API

```python
# Step 1: 변환 요청
POST https://convert.liberoai.net/api/convert
Headers: X-API-Key: lbr_SC7e-...
Body: multipart/form-data (file)
→ {"job_id": "...", "status": "pending"}

# Step 2: 상태 폴링
GET https://convert.liberoai.net/api/jobs/{job_id}
→ {"status": "completed", "download_url": "..."}

# Step 3: 결과 다운로드 (ZIP)
GET https://convert.liberoai.net/api/download/{job_id}
→ ZIP (content.html, content.md, metadata.json, images/)
```

### 6-3. Google Gemini API

```python
# RFP 분석 요청
model = "gemini-2.0-flash"   # 비용 효율 + 속도
# or "gemini-2.5-pro"        # 복잡한 분석 시

# 프롬프트 전략
# 1. 시스템 프롬프트: RFP 분석 전문가 역할 정의
# 2. 입력: HTML/MD 텍스트
# 3. 출력: 구조화된 JSON (스키마 지정)
```

### 6-4. AI 분석 응답 JSON 스키마

```json
{
  "basic_info": {
    "issuing_org": "발주기관명",
    "deadline": "2026-05-01T18:00:00",
    "project_summary": "사업 개요 요약",
    "project_scope": "사업 범위",
    "budget": 500000000
  },
  "eval_criteria": [
    { "category": "기술능력", "item": "추진전략", "score": 20 }
  ],
  "requirements": [
    { "id": "CPR-001", "category": "컨설팅", "name": "정보화 전략 검토", "description": "..." }
  ],
  "qualification": "참가 자격 요건 텍스트",
  "tech_requirements": ["클라우드 네이티브", "AI/빅데이터"],
  "poison_clauses": {
    "items": [
      {
        "category": "평가기준",
        "clause": "차등점수 2.5점 적용",
        "severity": "warning",
        "reason": "2.5점 차등은 업계 평균(1~2점) 대비 과도하며 소규모 업체에 불리",
        "source": "제안요청서 p.15"
      },
      {
        "category": "참가자격",
        "clause": "공동수급 및 하도급 불허",
        "severity": "danger",
        "reason": "두 가지 모두 불허 시 소규모 전문업체 참여 사실상 차단",
        "source": "입찰공고문 제4조"
      }
    ],
    "risk_level": "warning",
    "summary": "참가자격 제한이 다소 엄격하며, 차등점수제 배점이 높아 주의 필요"
  }
}
```

**독소조항 severity 기준:**

| 레벨 | 의미 | UI 표시 |
|------|------|--------|
| `safe` | 정상 범위 | 표시 안함 |
| `caution` | 주의 필요 | 노란 배지 |
| `warning` | 경고, 검토 필요 | 주황 배지 |
| `danger` | 위험, 참여 재고 | 빨간 배지 |

---

## 7. 화면 구성 설계

### 7-1. 페이지 라우팅

| 경로 | 페이지 | 권한 |
|------|--------|------|
| `/login` | 로그인 | 비인증 |
| `/dashboard` | 담당자 대시보드 | staff, admin |
| `/ceo` | CEO 대시보드 | admin only |
| `/bids/:id` | 공고 상세 + AI 분석 | staff, admin |

### 7-2. 담당자 대시보드 레이아웃

```
┌─────────────────────────────────────────────────────┐
│  G2B AI  [수동검색]                     👤 홍길동 ▼   │
├────────────────────────┬────────────────────────────┤
│   📋 현황 리스트 (좌측)  │  🎯 대상 리스트 (우측)      │
│                        │                            │
│  검색/필터: ________    │  상태 필터: [전체▼]         │
│                        │                            │
│  ┌──────────────────┐  │  ┌──────────────────────┐  │
│  │ 공고명           │→ │  │ 공고명          [상태]│  │
│  │ 발주기관 | 마감일 │  │  │ 담당: 홍길동         │  │
│  │ 예산: 3억        │  │  │ 마감: 05/01   ⚠경고  │  │
│  └──────────────────┘  │  │ 인원:_ 비용:_ 견적:_ │  │
│  ┌──────────────────┐  │  └──────────────────────┘  │
│  │ 공고명           │→ │  ┌──────────────────────┐  │
│  │ 발주기관 | 마감일 │  │  │ 공고명          [상태]│  │
│  │ 예산: 5억        │  │  │ 담당: 김철수         │  │
│  └──────────────────┘  │  │ 마감: 05/15   🔴위험 │  │
│  ...                   │  └──────────────────────┘  │
│                        │  ...                       │
├────────────────────────┴────────────────────────────┤
│  총 12건 수집 | 신규 3건 | 마감임박 2건               │
└─────────────────────────────────────────────────────┘
```

- `→` 버튼: 현황에서 대상으로 이동
- 독소조항 위험도 배지: ⚠(warning), 🔴(danger)
- 공고 클릭 → `/bids/:id` 상세 페이지로 이동

### 7-3. 공고 상세 페이지 레이아웃

```
┌─────────────────────────────────────────────────────┐
│  ← 뒤로   공고 상세                                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📌 기본 정보                                        │
│  ┌────────────────────────────────────────────────┐ │
│  │ 공고명: ○○시스템 구축 ISP 수립                   │ │
│  │ 발주기관: ○○부  |  마감: 2026-05-01 18:00       │ │
│  │ 예산: 5억원  |  상태: 검토중                      │ │
│  │ 위험도: ⚠ WARNING (독소조항 2건 발견)            │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  [AI 분석 요청] [목차 생성]  ← 각각 별도 버튼         │
│                                                     │
│  ┌─ 탭 ──────────────────────────────────────────┐  │
│  │ [AI 분석] [독소조항] [첨부파일] [제안목차]       │  │
│  ├────────────────────────────────────────────────┤  │
│  │                                                │  │
│  │  === AI 분석 탭 ===                            │  │
│  │  ▸ 사업 개요                                   │  │
│  │  ▸ 사업 범위                                   │  │
│  │  ▸ 평가항목/배점 (테이블)                       │  │
│  │  ▸ 참가 자격 요건                              │  │
│  │  ▸ 핵심 요구사항 목록                           │  │
│  │                                                │  │
│  │  === 독소조항 탭 ===                           │  │
│  │  종합 위험도: ⚠ WARNING                        │  │
│  │  ┌─────────┬──────────────────┬────────┐      │  │
│  │  │ 카테고리 │ 조항               │ 심각도 │      │  │
│  │  ├─────────┼──────────────────┼────────┤      │  │
│  │  │ 평가기준 │ 차등점수 2.5점     │ ⚠경고  │      │  │
│  │  │ 참가자격 │ 공동수급 불허      │ 🔴위험 │      │  │
│  │  └─────────┴──────────────────┴────────┘      │  │
│  │                                                │  │
│  │  === 제안목차 탭 ===                           │  │
│  │  (미생성 시) [목차 생성] 버튼                    │  │
│  │  (생성 후) L1~L4 트리 뷰 + [PDF 내보내기]       │  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 7-4. CEO 대시보드 레이아웃

```
┌─────────────────────────────────────────────────────┐
│  G2B AI  CEO 대시보드                   👤 대표 ▼    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📊 현황 요약                                        │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │
│  │검토필요│ │검토중 │ │진행중 │ │ 완료  │              │
│  │  3건  │ │ 2건  │ │ 4건  │ │ 8건  │              │
│  └──────┘ └──────┘ └──────┘ └──────┘              │
│                                                     │
│  📋 대상 리스트                                      │
│  ┌──────┬────────┬────┬────┬──────┬──────┬────┐    │
│  │공고명 │ 담당자  │인원│비용│ 견적  │ 마감일│상태│    │
│  ├──────┼────────┼────┼────┼──────┼──────┼────┤    │
│  │ ISP  │ 홍길동  │ 5명│ 2억│ 3.5억│05/01│⚠진행│    │
│  │ ISMP │ 김철수  │ 3명│ 1억│ 1.5억│05/15│검토 │    │
│  └──────┴────────┴────┴────┴──────┴──────┴────┘    │
│                                                     │
│  📅 마감 임박 (7일 이내)                              │
│  • ○○시스템 ISP (D-3) - 담당: 홍길동               │
│  • △△시스템 ISMP (D-7) - 담당: 김철수              │
└─────────────────────────────────────────────────────┘
```

---

## 8. 에러 처리 및 재시도 전략

### 8-1. 나라장터 API
- 타임아웃: 30초
- 실패 시: 3회 재시도 (exponential backoff: 5s → 15s → 45s)
- 일일 호출 한도 초과 시: 다음 스케줄까지 대기

### 8-2. 리브레AI API
- 변환 요청 타임아웃: 10초
- 폴링 타임아웃: 60초 (1초 간격)
- 실패 시: `conversion_status = 'failed'`, 수동 재시도 가능
- 일일 50회 한도 관리: DB에서 당일 사용 횟수 카운트

### 8-3. Gemini API
- 타임아웃: 60초 (NFR-01 성능 요구사항)
- 실패 시: 2회 재시도
- Rate limit: 429 응답 시 30초 대기 후 재시도
- JSON 파싱 실패: `analysis_status = 'failed'`, 원본 응답 `raw_analysis`에 보존

---

## 9. 보안 설계

### 9-1. 인증/인가
- JWT Access Token: 만료 30분
- JWT Refresh Token: 만료 7일, httpOnly 쿠키
- 비밀번호: bcrypt 해싱 (cost factor 12)
- 역할 기반 접근: `staff`(담당자), `admin`(CEO)

### 9-2. API 보안
- 모든 API에 JWT 인증 미들웨어
- admin 전용 엔드포인트: `invite`, `dashboard/stats`
- CORS: 프론트엔드 도메인만 허용

### 9-3. 환경변수 관리
```env
# .env (절대 커밋 금지)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/g2b_ai
JWT_SECRET_KEY=...
G2B_API_KEY=...              # 나라장터 공공데이터포털 키
LIBREAI_API_KEY=lbr_SC7e-... # 리브레AI
GEMINI_API_KEY=...           # Google Gemini
```

---

## 10. MVP 구현 우선순위

### Phase 1: 기반 (1주)
- [ ] 프로젝트 초기 셋업 (backend + frontend)
- [ ] PostgreSQL + 테이블 생성
- [ ] JWT 인증 (로그인, 관리자 초대)

### Phase 2: 공고 수집 (1주)
- [ ] 나라장터 API 연동 (수동 검색)
- [ ] 공고 목록/상세 API
- [ ] 자동 수집 스케줄러

### Phase 3: HWP 변환 + AI 분석 (1~2주)
- [ ] 리브레AI HWP 변환 연동
- [ ] Gemini RFP 분석 프롬프트 설계
- [ ] 분석 결과 저장/조회 API

### Phase 4: 대시보드 UI (1주)
- [ ] 담당자 대시보드 (현황 + 대상 패널)
- [ ] CEO 대시보드 (대상 + 통계)
- [ ] 공고 상세 + AI 분석 결과 뷰

### Phase 5: 고도화 (이후)
- [ ] 슬랙/이메일 알림
- [ ] pgvector 유사 공고 검색
- [ ] 제안목차 자동 생성

---

## 11. 기술 선택 근거

| 선택 | 이유 |
|------|------|
| **FastAPI** | async 네이티브, 자동 Swagger 문서, Pydantic 통합 |
| **asyncpg** | PostgreSQL 전용, SQLAlchemy async보다 빠름, raw SQL 직접 제어 |
| **APScheduler** | FastAPI와 동일 프로세스 내 실행, 별도 Celery 불필요 (소규모 트래픽) |
| **React 19 + Vite** | 빠른 HMR, TypeScript strict |
| **Ant Design** | 테이블/폼/레이아웃 컴포넌트 풍부, 대시보드에 적합 |
| **TanStack Query** | 서버 상태 캐싱, 자동 리페치, 로딩/에러 상태 관리 |
| **Gemini Flash** | 비용 효율 (Pro 대비 1/10), RFP 분석에 충분한 성능 |
| **리브레AI** | HWP 표 보존 최선, 무료 50회/일 (하루 20건 처리에 충분) |
