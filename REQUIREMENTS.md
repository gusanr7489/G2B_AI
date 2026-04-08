# G2B_AI — 요구사항 명세서

## 1. 프로젝트 개요

### 배경
공공 입찰 제안요청서(RFP) 분석은 과장급 이상의 전문 인력이 필요하나, 매건 투입이 불가능하여 검토 누락이 발생한다. AI가 RFP 분석을 보조하여 초급 인력도 핵심 정보를 파악하고 의사결정을 지원할 수 있는 시스템을 구축한다.

### 목적
- 나라장터 용역 공고(IT 컨설팅)를 자동 수집 및 AI 분석
- 제안요청서에서 핵심 정보를 추출하고, 제안목차를 자동 생성
- 담당자용/CEO용 대시보드로 입찰 의사결정 지원

### 대상 범위
- **공고 유형**: 용역 공고 (물품류 제외), IT 컨설팅 사업
- **처리 규모**: 하루 최대 20건, 보통 10건 미만
- **사용자 규모**: 소규모(5명 이하)로 시작 → 20명 이상으로 확장

---

## 2. 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | Python 3.11+, FastAPI |
| 프론트엔드 | React 19, TypeScript, Vite, Ant Design |
| DB | PostgreSQL + pgvector |
| AI/LLM | Google Gemini API |
| HWP 변환 | 1순위: 리브레AI API (50건/일 무료), 2순위: 로컬 라이브러리 |
| 상태 관리 | TanStack Query |
| 인증 | 로그인 기반 역할 구분 (담당자/CEO) |
| 알림 | 이메일/슬랙 연동 |

---

## 3. 기능 요구사항

### FR-01. 사용자 인증 및 권한 관리
- 로그인/로그아웃
- 역할 구분: **담당자(Staff)**, **CEO(Admin)**
- 역할별 대시보드 및 기능 접근 제어

### FR-02. 공고 자동 수집 (모니터링)
- 나라장터 API를 통한 신규 용역 공고 주기적 자동 수집
- 수집 조건 설정 (키워드, 분류, 예산 범위 등)
- 신규 공고 발생 시 이메일/슬랙 알림 발송
- 수동 검색도 병행 지원

### FR-03. HWP 첨부파일 변환 및 텍스트 추출
- 리브레AI API를 통한 HWP → 텍스트 변환 (1순위)
- 로컬 라이브러리 기반 변환 (2순위 fallback)
- **표(Table) 데이터 보존**이 핵심 (기존 HWP 표 깨짐 문제 해결)
- PDF 첨부파일 텍스트 추출 지원

### FR-04. AI 기반 제안요청서(RFP) 분석
- **핵심 추출 항목**:
  - 발주 기관
  - 입찰 마감일시 (**최우선 추출 대상**)
  - 사업 개요 및 범위
  - 평가 항목 및 배점
  - 참가 자격 요건
  - 기술 요구사항
- 나라장터 공고의 주요 패턴 인식 및 분석
- 과업지시서 기반 세부과업 목록(요구사항) 도출

### FR-05. 제안목차 자동 생성
- 평가항목 배점 포함, Level 1~4 계층 구조
- 제안요청서에 명시된 항목은 **반드시 모두 포함**
- ISP/ISMP 공통 가이드라인(행정안전부) 기반 작성
- ISMP 사업은 고정 프로세스에 맞게 작성
- 제안추진전략과 일관성 있게 매핑

### FR-06. 담당자 대시보드
- **좌측: 현황 리스트**
  - 자동 수집된 신규 공고 목록
  - 공고 기본 정보 표시 (공고명, 발주기관, 마감일 등)
- **우측: 대상 리스트**
  - 담당자가 선별한 검토 대상 공고
  - 상태 관리: `검토 필요` → `검토 중` → `진행 중` → `완료`
  - 불필요 공고 삭제 기능
- **현황 → 대상 이동 버튼 (`→`)**
  - 현황 리스트에서 선택한 공고를 대상 리스트로 이동
- 개별 공고 클릭 시 AI 분석 결과 상세 보기
- 담당자가 수동 입력하는 필드:
  - 필요 인원, 사무실, 소요비용, 사업견적

### FR-07. CEO 대시보드
- **대상 리스트만 표시** (현황 리스트 없음)
- 각 공고별 표시 정보:
  - 검토 담당자명
  - 필요 인원
  - 사무실
  - 소요비용
  - 사업견적
  - 입찰 마감일
  - 진행 상태
- 전체 현황 통계/요약 뷰

### FR-08. 유사 공고 검색 (pgvector)
- 공고 텍스트를 벡터 임베딩으로 저장
- 과거 공고/제안서와 유사도 기반 검색
- 유사 공고의 분석 결과 참조 기능

### FR-09. 제안목차 출력
- 생성된 제안목차를 보기 좋게 화면에 표시
- 인쇄/PDF 내보내기 지원

---

## 4. 비기능 요구사항

### NFR-01. 성능
- 공고 분석(AI) 응답: 60초 이내
- 대시보드 로딩: 3초 이내
- HWP 변환: 30초 이내

### NFR-02. 보안
- 제안서 본문 데이터는 AI 학습에 사용하지 않음 (Gemini API 정책 확인)
- 사용자 인증 토큰 기반 (JWT)
- API 키 환경변수 관리

### NFR-03. 확장성
- 소규모(5명) → 20명 이상 확장 가능한 구조
- PostgreSQL 기반으로 동시 접속 지원

### NFR-04. 가용성
- 자동 수집 스케줄러 안정 동작 (실패 시 재시도)
- 리브레AI API 장애 시 로컬 변환 fallback

---

## 5. 사용자 스토리

### 담당자
- **US-01**: 담당자로서, 매일 자동 수집된 신규 공고 목록을 확인하고, 검토할 만한 공고를 대상 리스트로 넘기고 싶다.
- **US-02**: 담당자로서, 선별한 공고의 RFP를 AI로 분석하여 핵심 정보(마감일, 요구사항 등)를 빠르게 파악하고 싶다.
- **US-03**: 담당자로서, AI가 생성한 제안목차를 확인하고, 평가항목이 빠짐없이 반영되었는지 검증하고 싶다.
- **US-04**: 담당자로서, 공고 상태를 `검토 필요` → `검토 중` → `진행 중` → `완료`로 관리하고 싶다.
- **US-05**: 담당자로서, 필요 인원/사무실/비용/견적 정보를 입력하여 CEO에게 보고하고 싶다.
- **US-06**: 담당자로서, 과거 유사 공고를 검색하여 이전 분석 결과를 참고하고 싶다.

### CEO
- **US-07**: CEO로서, 현재 진행 중인 입찰 건들의 전체 현황을 한눈에 파악하고 싶다.
- **US-08**: CEO로서, 각 공고별 담당자, 필요 인원, 비용, 마감일 등 핵심 정보를 확인하여 의사결정하고 싶다.

### 공통
- **US-09**: 사용자로서, 새로운 용역 공고가 등록되면 이메일/슬랙으로 알림을 받고 싶다.
- **US-10**: 사용자로서, 제안목차를 PDF로 출력하고 싶다.

---

## 6. 데이터 모델 (초안)

### users
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| email | VARCHAR | 로그인 이메일 |
| password_hash | VARCHAR | 비밀번호 해시 |
| name | VARCHAR | 이름 |
| role | ENUM | staff / admin(CEO) |
| created_at | TIMESTAMP | |

### bids (수집된 공고)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| bid_ntce_no | VARCHAR | 공고번호 |
| bid_ntce_ord | VARCHAR | 공고차수 |
| bid_ntce_nm | VARCHAR | 공고명 |
| ntce_instt_nm | VARCHAR | 발주기관 |
| bid_close_dt | TIMESTAMP | 입찰마감일시 |
| asign_bdgt_amt | BIGINT | 배정예산 |
| raw_data | JSONB | 원본 API 응답 |
| extracted_text | TEXT | 첨부파일 추출 텍스트 |
| embedding | vector(768) | 텍스트 임베딩 (pgvector) |
| status | VARCHAR | new / collected |
| created_at | TIMESTAMP | |

### bid_targets (대상 리스트)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| bid_id | FK → bids | |
| assignee_id | FK → users | 담당자 |
| status | ENUM | 검토필요 / 검토중 / 진행중 / 완료 |
| required_staff | INTEGER | 필요 인원 |
| office_info | VARCHAR | 사무실 |
| estimated_cost | BIGINT | 소요비용 |
| bid_estimate | BIGINT | 사업견적 |
| notes | TEXT | 메모 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### analyses (AI 분석 결과)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| bid_id | FK → bids | |
| issuing_org | VARCHAR | 발주기관 (추출) |
| deadline | TIMESTAMP | 마감일시 (추출) |
| project_summary | TEXT | 사업 개요 |
| eval_criteria | JSONB | 평가항목/배점 |
| requirements | JSONB | 세부과업 목록 |
| qualification | TEXT | 참가 자격 요건 |
| raw_analysis | JSONB | AI 원본 응답 |
| created_at | TIMESTAMP | |

### proposal_outlines (제안목차)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| analysis_id | FK → analyses | |
| outline_data | JSONB | L1~L4 계층 구조 목차 |
| ismp_type | BOOLEAN | ISMP 사업 여부 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### monitoring_configs (자동 수집 설정)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| user_id | FK → users | |
| keywords | JSONB | 수집 키워드 |
| categories | JSONB | 분류 필터 |
| budget_min | BIGINT | 최소 예산 |
| budget_max | BIGINT | 최대 예산 |
| is_active | BOOLEAN | 활성 여부 |
| cron_schedule | VARCHAR | 수집 주기 |

### notifications (알림 이력)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| user_id | FK → users | |
| bid_id | FK → bids | |
| channel | VARCHAR | email / slack |
| sent_at | TIMESTAMP | |
| status | VARCHAR | sent / failed |

---

## 7. 제약사항 및 미결 항목

### 제약사항
- 제안서 본문 작성은 데이터 보안 이슈로 **현 단계에서 제외**
- 추후 기업 제안서 목차 샘플을 받아 목차 리스트까지 AI로 생성 (하네스 엔지니어링)
- HWP 표 데이터 보존은 리브레AI API 성능에 의존

### 완료 항목
- [x] ISP/ISMP 공통 가이드라인 문서 확보 (제9판, NIA 2025)
- [x] 제안요청서 샘플 + 제안목차 샘플 수집 (ISP 2건, ISMP 2건)
- [x] 리브레AI API 키 발급 및 테스트 (HWP→HTML+MD ZIP, 일일 50회)
- [x] 사용자 회원가입 → **관리자 초대 방식** 확정

### 후순위 항목 (MVP 이후)
- [ ] 슬랙 워크스페이스 웹훅 URL 확보
- [ ] 이메일 발송 서비스 선정 (SMTP / SendGrid 등)
- [ ] Gemini API 임베딩 모델 선정 및 pgvector 유사 공고 검색
- [ ] 제안목차 자동 생성 (하네스 엔지니어링)

---

## 8. 다음 단계

1. `/sc:design` → 아키텍처 설계
2. `/sc:workflow` → 구현 워크플로우 수립
3. 참고 자료(가이드라인, 샘플) 확보 후 AI 프롬프트 설계
