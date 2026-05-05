import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import get_db
from services.g2b_service import save_bids_to_db, search_bids

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

scheduler = AsyncIOScheduler(timezone=KST)


IT_KEYWORDS = [
    "ISP", "ISMP", "정보화전략계획", "정보전략",
    "정보시스템", "정보보호", "컨설팅",
    "소프트웨어", "시스템구축", "전자정부",
    "클라우드", "인공지능", "정보화",
    "디지털전환", "스마트시티", "빅데이터",
    "플랫폼 구축", "ERP",
]

# 공고명에 이 키워드가 포함되면 IT 컨설팅이 아니므로 제외
EXCLUDE_KEYWORDS = [
    "건설", "토목", "도로", "교량", "상하수도", "폐기물",
    "조경", "놀이터", "체육", "급식", "식품", "의료",
    "수학여행", "문화탐방", "관광", "숙박", "임차",
    "발굴", "보수공사", "시설물", "측량", "환경영향",
]


def is_it_consulting_bid(bid_name: str) -> bool:
    """공고명이 IT 컨설팅 관련인지 판별"""
    name_lower = bid_name.lower()
    if any(ex in name_lower for ex in EXCLUDE_KEYWORDS):
        return False
    return any(kw.lower() in name_lower for kw in IT_KEYWORDS)


async def collect_recent_bids():
    """최근 N시간 내 IT 컨설팅 관련 신규 공고 수집 → DB 저장"""
    try:
        db = await get_db()

        now = datetime.now(KST)
        bgn = now - timedelta(hours=8)
        bgn_str = bgn.strftime("%Y%m%d%H%M")
        end_str = now.strftime("%Y%m%d%H%M")

        logger.info(f"자동 수집 시작: {bgn_str} ~ {end_str}")

        total_found = 0
        total_saved = 0

        for kw in IT_KEYWORDS:
            result = await search_bids(
                keyword=kw,
                inqry_bgn_dt=bgn_str,
                inqry_end_dt=end_str,
                num_of_rows=100,
            )
            if result["items"]:
                saved = await save_bids_to_db(db, result["items"])
                total_found += result["total_count"]
                total_saved += saved

        logger.info(
            f"자동 수집 완료: {total_found}건 조회, {total_saved}건 신규 저장"
        )

    except Exception as e:
        logger.error(f"자동 수집 실패: {e}", exc_info=True)


def start_scheduler():
    """스케줄러 시작: 매일 10:00, 14:00, 20:00 (KST)"""
    scheduler.add_job(
        collect_recent_bids,
        CronTrigger(hour="10,14,20", minute=0, timezone=KST),
        id="collect_bids",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("공고 수집 스케줄러 시작 (10:00, 14:00, 20:00 KST)")


def stop_scheduler():
    """스케줄러 종료"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("공고 수집 스케줄러 종료")
