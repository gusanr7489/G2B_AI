import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import get_db
from services.g2b_service import save_bids_to_db, search_bids

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

scheduler = AsyncIOScheduler(timezone=KST)


async def collect_recent_bids():
    """최근 N시간 내 신규 공고 수집 → DB 저장"""
    try:
        db = await get_db()

        now = datetime.now(KST)
        bgn = now - timedelta(hours=8)
        bgn_str = bgn.strftime("%Y%m%d%H%M")
        end_str = now.strftime("%Y%m%d%H%M")

        logger.info(f"자동 수집 시작: {bgn_str} ~ {end_str}")

        result = await search_bids(
            inqry_bgn_dt=bgn_str,
            inqry_end_dt=end_str,
            num_of_rows=100,
        )

        saved = await save_bids_to_db(db, result["items"])
        logger.info(
            f"자동 수집 완료: {result['total_count']}건 조회, {saved}건 신규 저장"
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
