import logging
from datetime import datetime, timedelta, timezone

from services.g2b_service import (
    extract_attachments_from_raw,
    save_attachments_to_db,
    save_bids_to_db,
    search_bids,
)
from services.hwp_service import download_and_convert
from services.analysis_service import analyze_rfp
from services.scheduler_service import IT_KEYWORDS

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


async def run_collect_pipeline(bid_id: int, db) -> None:
    """단일 공고 처리: 첨부파일 수집 → HWP 변환 → AI 분석 (직렬)"""
    try:
        exists = await db.fetchval("SELECT id FROM bids WHERE id = $1", bid_id)
        if not exists:
            logger.error(f"공고를 찾을 수 없음: bid_id={bid_id}")
            return

        # 1. raw_data에서 첨부파일 URL 추출
        await db.execute("UPDATE bids SET status = 'collecting' WHERE id = $1", bid_id)
        raw = await db.fetchval("SELECT raw_data FROM bids WHERE id = $1", bid_id)
        attachments = extract_attachments_from_raw(raw)
        if not attachments:
            logger.info(f"첨부파일 없음: bid_id={bid_id}")
            await db.execute("UPDATE bids SET status = 'no_file' WHERE id = $1", bid_id)
            return

        await save_attachments_to_db(db, bid_id, attachments)
        logger.info(f"첨부파일 {len(attachments)}건 저장: bid_id={bid_id}")

        # 2. HWP/PDF 변환
        await db.execute("UPDATE bids SET status = 'converting' WHERE id = $1", bid_id)
        has_converted = False
        att_rows = await db.fetch(
            "SELECT id, file_name, file_type, file_url FROM bid_attachments WHERE bid_id = $1",
            bid_id,
        )

        for att in att_rows:
            file_type = (att["file_type"] or "").lower()
            try:
                if file_type == "hwp":
                    result = await download_and_convert(att["file_url"])
                    await db.execute(
                        """
                        UPDATE bid_attachments
                        SET converted_html = $1, converted_md = $2, conversion_status = 'completed'
                        WHERE id = $3
                        """,
                        result["html"],
                        result["md"],
                        att["id"],
                    )
                    has_converted = True
                    logger.info(f"HWP 변환 완료: {att['file_name']}")
                elif file_type == "pdf":
                    result = await download_and_convert(att["file_url"])
                    await db.execute(
                        """
                        UPDATE bid_attachments
                        SET converted_md = $1, conversion_status = 'skipped'
                        WHERE id = $2
                        """,
                        result["md"],
                        att["id"],
                    )
                else:
                    await db.execute(
                        "UPDATE bid_attachments SET conversion_status = 'skipped' WHERE id = $1",
                        att["id"],
                    )
            except Exception as e:
                logger.error(f"변환 실패 ({att['file_name']}): {e}")
                await db.execute(
                    "UPDATE bid_attachments SET conversion_status = 'failed' WHERE id = $1",
                    att["id"],
                )

        # 3. 변환 성공 시 AI 분석
        if has_converted:
            await db.execute("UPDATE bids SET status = 'analyzing' WHERE id = $1", bid_id)
            try:
                await analyze_rfp(bid_id, db)
                await db.execute("UPDATE bids SET status = 'analyzed' WHERE id = $1", bid_id)
                logger.info(f"AI 분석 완료: bid_id={bid_id}")
                return
            except Exception as e:
                logger.error(f"AI 분석 실패 (bid_id={bid_id}): {e}")
                await db.execute("UPDATE bids SET status = 'analysis_failed' WHERE id = $1", bid_id)
                return

        await db.execute("UPDATE bids SET status = 'completed' WHERE id = $1", bid_id)

    except Exception as e:
        logger.error(f"처리 실패 (bid_id={bid_id}): {e}", exc_info=True)
        await db.execute("UPDATE bids SET status = 'failed' WHERE id = $1", bid_id)


async def run_batch_collect(db) -> dict:
    """IT 컨설팅 공고만 수집: IT_KEYWORDS로 나라장터 검색 → 직렬 처리"""
    now = datetime.now(KST)
    bgn = now - timedelta(hours=24)
    bgn_str = bgn.strftime("%Y%m%d%H%M")
    end_str = now.strftime("%Y%m%d%H%M")

    total_found = 0
    total_saved = 0

    # IT 키워드별로 나라장터 API 검색 (IT 공고만 수집)
    for kw in IT_KEYWORDS:
        try:
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
        except Exception as e:
            logger.error(f"키워드 '{kw}' 수집 실패: {e}")

    logger.info(f"일괄 수집 완료: {total_found}건 조회, {total_saved}건 신규 저장")

    # 신규 공고마다 첨부파일 수집 → 변환 → 분석 직렬 처리
    new_bids = await db.fetch(
        "SELECT id FROM bids WHERE status = 'new' ORDER BY id"
    )
    for bid in new_bids:
        await run_collect_pipeline(bid["id"], db)

    return {"found": total_found, "saved": total_saved}
