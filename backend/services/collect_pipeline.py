import logging
from datetime import datetime, timedelta, timezone

from services.g2b_service import (
    extract_attachments_from_raw,
    save_attachments_to_db,
    save_bids_to_db,
    search_bids,
)
from services.hwp_service import download_and_convert
from services.scheduler_service import IT_KEYWORDS

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


async def _refetch_raw_data(bid_id: int, db) -> dict | None:
    """raw_data가 없는 공고의 경우 나라장터 API에서 다시 검색하여 보충"""
    row = await db.fetchrow(
        "SELECT bid_ntce_no, bid_ntce_ord FROM bids WHERE id = $1", bid_id
    )
    if not row or not row["bid_ntce_no"]:
        return None

    try:
        result = await search_bids(
            keyword="",
            inqry_bgn_dt="202601010000",
            inqry_end_dt="202612312359",
            num_of_rows=10,
        )
        for item in result["items"]:
            if item.get("bidNtceNo") == row["bid_ntce_no"]:
                import json
                raw_json = json.dumps(item, ensure_ascii=False)
                await db.execute(
                    "UPDATE bids SET raw_data = $1 WHERE id = $2",
                    raw_json, bid_id,
                )
                logger.info(f"raw_data 보충 완료: bid_id={bid_id}")
                return item

        # 공고번호로 직접 검색 재시도
        result2 = await search_bids(
            keyword=row["bid_ntce_no"],
            inqry_bgn_dt="202601010000",
            inqry_end_dt="202612312359",
            num_of_rows=10,
        )
        for item in result2["items"]:
            if item.get("bidNtceNo") == row["bid_ntce_no"]:
                import json
                raw_json = json.dumps(item, ensure_ascii=False)
                await db.execute(
                    "UPDATE bids SET raw_data = $1 WHERE id = $2",
                    raw_json, bid_id,
                )
                logger.info(f"raw_data 보충 완료 (재검색): bid_id={bid_id}")
                return item
    except Exception as e:
        logger.warning(f"raw_data 보충 실패 (bid_id={bid_id}): {e}")

    return None


async def run_collect_pipeline(bid_id: int, db) -> None:
    """단일 공고: 첨부파일 URL 추출 + DB 저장 → 변환"""
    try:
        row = await db.fetchrow("SELECT id, status FROM bids WHERE id = $1", bid_id)
        if not row:
            logger.error(f"공고를 찾을 수 없음: bid_id={bid_id}")
            return

        # 이미 변환 완료된 첨부파일이 있으면 스킵
        converted_count = await db.fetchval(
            "SELECT COUNT(*) FROM bid_attachments WHERE bid_id = $1 AND conversion_status = 'completed'",
            bid_id,
        )
        if converted_count > 0:
            logger.info(f"이미 수집/변환 완료: bid_id={bid_id}")
            await db.execute("UPDATE bids SET status = 'completed' WHERE id = $1", bid_id)
            return

        await db.execute("UPDATE bids SET status = 'collecting' WHERE id = $1", bid_id)
        raw = await db.fetchval("SELECT raw_data FROM bids WHERE id = $1", bid_id)

        # raw_data가 없으면 나라장터 API에서 다시 가져오기
        if not raw:
            logger.info(f"raw_data 없음, 나라장터에서 재검색: bid_id={bid_id}")
            refetched = await _refetch_raw_data(bid_id, db)
            if refetched:
                raw = refetched

        attachments = extract_attachments_from_raw(raw)
        if not attachments:
            logger.info(f"첨부파일 없음: bid_id={bid_id}")
            await db.execute("UPDATE bids SET status = 'no_file' WHERE id = $1", bid_id)
            return

        await save_attachments_to_db(db, bid_id, attachments)
        logger.info(f"첨부파일 {len(attachments)}건 저장: bid_id={bid_id}")
        await db.execute("UPDATE bids SET status = 'collected' WHERE id = $1", bid_id)

    except Exception as e:
        logger.error(f"수집 실패 (bid_id={bid_id}): {e}", exc_info=True)
        await db.execute("UPDATE bids SET status = 'failed' WHERE id = $1", bid_id)


async def run_convert(bid_id: int, db) -> None:
    """첨부파일 변환만 수행 (AI 분석은 수동 트리거)"""
    try:
        # 이미 변환 완료된 경우 스킵
        converted_count = await db.fetchval(
            """
            SELECT COUNT(*) FROM bid_attachments
            WHERE bid_id = $1 AND conversion_status = 'completed'
            """,
            bid_id,
        )
        if converted_count > 0:
            logger.info(f"이미 변환 완료: bid_id={bid_id}")
            await db.execute("UPDATE bids SET status = 'completed' WHERE id = $1", bid_id)
            return

        # 첨부파일이 없으면 먼저 수집
        att_count = await db.fetchval(
            "SELECT COUNT(*) FROM bid_attachments WHERE bid_id = $1", bid_id
        )
        if att_count == 0:
            await run_collect_pipeline(bid_id, db)
            return  # run_collect_pipeline이 재귀적으로 run_convert 호출

        # 첨부파일 변환 (HWP/PDF → 리브레AI)
        await db.execute("UPDATE bids SET status = 'converting' WHERE id = $1", bid_id)
        att_rows = await db.fetch(
            """
            SELECT id, file_name, file_type, file_url FROM bid_attachments
            WHERE bid_id = $1 AND conversion_status IS DISTINCT FROM 'completed'
            """,
            bid_id,
        )

        for att in att_rows:
            file_type = (att["file_type"] or "").lower()
            try:
                if file_type == "pdf":
                    # PDF는 Gemini가 직접 읽으므로 변환 불필요
                    await db.execute(
                        "UPDATE bid_attachments SET conversion_status = 'completed' WHERE id = $1",
                        att["id"],
                    )
                    logger.info(f"PDF 변환 스킵 (Gemini 직접 처리): {att['file_name']}")
                elif file_type in ("hwp", "hwpx"):
                    result = await download_and_convert(att["file_url"], att["file_name"])
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
                    logger.info(f"HWP 변환 완료: {att['file_name']}")
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

        # 변환 결과에 따라 상태 설정
        success = await db.fetchval(
            "SELECT COUNT(*) FROM bid_attachments WHERE bid_id = $1 AND conversion_status = 'completed'",
            bid_id,
        )
        if success > 0:
            await db.execute("UPDATE bids SET status = 'completed' WHERE id = $1", bid_id)
        else:
            await db.execute("UPDATE bids SET status = 'collected' WHERE id = $1", bid_id)
            logger.warning(f"변환 성공 파일 없음, collected 상태 유지: bid_id={bid_id}")

    except Exception as e:
        logger.error(f"변환 실패 (bid_id={bid_id}): {e}", exc_info=True)
        await db.execute("UPDATE bids SET status = 'failed' WHERE id = $1", bid_id)


async def run_batch_collect(db) -> dict:
    """IT 컨설팅 공고 수집만 수행 (변환/분석 X)"""
    now = datetime.now(KST)
    bgn = now - timedelta(days=7)
    bgn_str = bgn.strftime("%Y%m%d%H%M")
    end_str = now.strftime("%Y%m%d%H%M")

    total_found = 0
    total_saved = 0

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

    # 신규 공고 첨부파일 URL만 추출/저장
    new_bids = await db.fetch(
        "SELECT id FROM bids WHERE status = 'new' ORDER BY id"
    )
    for bid in new_bids:
        await run_collect_pipeline(bid["id"], db)

    return {"found": total_found, "saved": total_saved}
