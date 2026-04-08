from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db, close_db
from services.scheduler_service import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    await init_db()
    start_scheduler()
    yield
    # 종료
    stop_scheduler()
    await close_db()


app = FastAPI(
    title="G2B AI",
    description="나라장터 공고 AI 분석 플랫폼",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터 등록 (Phase별로 추가)
from routers import auth
app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
from routers import bids
app.include_router(bids.router, prefix="/api/bids", tags=["공고"])
from routers import analyses
app.include_router(analyses.router, prefix="/api/analyses", tags=["분석"])
from routers import targets
app.include_router(targets.router, prefix="/api/targets", tags=["대상"])
from routers import dashboard
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["대시보드"])


@app.get("/")
async def root():
    return {"message": "G2B AI API 서버 실행 중"}


@app.get("/health")
async def health():
    return {"status": "ok"}
