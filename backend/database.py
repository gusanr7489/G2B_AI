import asyncpg
from config import get_settings

# 모듈 레벨 연결 풀 (앱 시작 시 초기화)
pool: asyncpg.Pool | None = None


async def init_db():
    """앱 시작 시 DB 연결 풀 생성"""
    global pool
    settings = get_settings()
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
    )


async def close_db():
    """앱 종료 시 연결 풀 해제"""
    global pool
    if pool:
        await pool.close()
        pool = None


async def get_db() -> asyncpg.Pool:
    """라우터에서 사용할 DB 풀 의존성"""
    if pool is None:
        raise RuntimeError("DB 연결 풀이 초기화되지 않았습니다")
    return pool
