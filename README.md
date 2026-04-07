# G2B_AI — AI 기반 나라장터 공고 분석 플랫폼

조달청(나라장터) 입찰공고를 AI로 분석하여 입찰 적합성을 평가하고, 제안서 초안을 자동 생성하는 웹 플랫폼입니다.

## 주요 기능

- 나라장터 입찰공고 검색 및 상세 조회
- HWP/PDF 첨부파일 텍스트 추출
- AI 기반 공고 적합성 평가 (0~100점)
- 제안서 초안 자동 생성
- 평가 이력 관리 및 키워드/템플릿 설정

## 기술 스택

- **백엔드**: Python 3.11+, FastAPI, aiosqlite, httpx
- **프론트엔드**: React 19, TypeScript, Vite, Ant Design, TanStack Query
- **AI**: Google Gemini API
- **DB**: SQLite
- **문서 변환**: LibreOffice headless, PyMuPDF, pyhwp

## 실행 방법

### 백엔드
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 프론트엔드
```bash
cd frontend
npm install
npm run dev
```

## 팀원

- gusanr7489
