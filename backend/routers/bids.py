import json
from urllib.parse import quote

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from database import get_db
from dependencies import get_current_user
from schemas.bid import (
    BidCollectRequest,
    BidDetail,
    BidListResponse,
    BidSearchParams,
    BidSummary,
)
from services.g2b_service import parse_bid_item, save_bids_to_db, search_bids
from services.collect_pipeline import run_batch_collect, run_collect_pipeline, run_convert

router = APIRouter()


@router.get("", response_model=BidListResponse)
async def list_bids(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="공고명 검색"),
    org: str = Query("", description="수요기관 검색"),
    analysis_status: str = Query("", description="분석 상태 필터 (analyzed/outline)"),
    hide_expired: bool = Query(False, description="마감된 공고 숨김"),
    min_price: int = Query(0, description="최소 금액"),
    max_price: int = Query(0, description="최대 금액"),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """DB에 수집된 공고 목록 조회 (페이지네이션, 필터)"""
    conditions = []
    params = []
    idx = 1

    if keyword:
        conditions.append(f"b.bid_ntce_nm ILIKE ${idx}")
        params.append(f"%{keyword}%")
        idx += 1

    if org:
        conditions.append(f"(b.dminstt_nm ILIKE ${idx} OR b.ntce_instt_nm ILIKE ${idx})")
        params.append(f"%{org}%")
        idx += 1

    if hide_expired:
        conditions.append(f"(b.bid_close_dt IS NULL OR b.bid_close_dt > NOW())")

    if min_price > 0:
        conditions.append(f"COALESCE(b.presmpt_prce, b.asign_bdgt_amt, 0) >= ${idx}")
        params.append(min_price)
        idx += 1

    if max_price > 0:
        conditions.append(f"COALESCE(b.presmpt_prce, b.asign_bdgt_amt, 0) <= ${idx}")
        params.append(max_price)
        idx += 1

    if analysis_status == "analyzed":
        conditions.append("a.analysis_status = 'completed'")
    elif analysis_status == "unanalyzed":
        conditions.append("(a.id IS NULL OR a.analysis_status <> 'completed')")
    elif analysis_status == "outline":
        conditions.append("po.id IS NOT NULL")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = await db.fetchval(
        f"""
        SELECT COUNT(*) FROM bids b
        LEFT JOIN analyses a ON a.bid_id = b.id
        LEFT JOIN proposal_outlines po ON po.analysis_id = a.id
        {where}
        """,
        *params,
    )

    offset = (page - 1) * size
    rows = await db.fetch(
        f"""
        SELECT b.id, b.bid_ntce_no, b.bid_ntce_ord, b.bid_ntce_nm,
               b.ntce_instt_nm, b.dminstt_nm, b.bid_close_dt,
               b.asign_bdgt_amt, b.presmpt_prce, b.created_at,
               a.analysis_status AS analysis_status,
               CASE
                 WHEN po.id IS NOT NULL THEN '목차완료'
                 WHEN a.analysis_status = 'completed' THEN '분석완료'
                 WHEN a.analysis_status = 'processing' THEN '검토중'
                 WHEN a.analysis_status = 'failed' THEN '분석실패'
                 ELSE ''
               END AS display_status
        FROM bids b
        LEFT JOIN analyses a ON a.bid_id = b.id
        LEFT JOIN proposal_outlines po ON po.analysis_id = a.id
        {where}
        ORDER BY b.created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
        size,
        offset,
    )

    items = [BidSummary(**dict(r)) for r in rows]
    return BidListResponse(items=items, total=total, page=page, size=size)


@router.get("/{bid_id}", response_model=BidDetail)
async def get_bid(
    bid_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """공고 상세 조회 (첨부파일 포함)"""
    row = await db.fetchrow(
        """
        SELECT id, bid_ntce_no, bid_ntce_ord, bid_ntce_nm,
               ntce_instt_nm, dminstt_nm, bid_close_dt,
               asign_bdgt_amt, presmpt_prce, bid_ntce_url,
               raw_data, status, created_at
        FROM bids WHERE id = $1
        """,
        bid_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다")

    attachments = await db.fetch(
        """
        SELECT id, file_name, file_type, file_url,
               conversion_status, created_at
        FROM bid_attachments WHERE bid_id = $1
        """,
        bid_id,
    )

    bid = dict(row)
    # asyncpg returns JSON as string, ensure it's dict
    if isinstance(bid.get("raw_data"), str):
        bid["raw_data"] = json.loads(bid["raw_data"])
    bid["attachments"] = [dict(a) for a in attachments]
    return BidDetail(**bid)


@router.post("/search")
async def search_g2b(
    params: BidSearchParams,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """나라장터 수동 검색 → DB 저장"""
    result = await search_bids(
        keyword=params.keyword,
        inqry_bgn_dt=params.inqry_bgn_dt,
        inqry_end_dt=params.inqry_end_dt,
        page_no=params.page_no,
        num_of_rows=params.num_of_rows,
    )

    saved = await save_bids_to_db(db, result["items"])

    return {
        "total_found": result["total_count"],
        "saved": saved,
        "message": f"나라장터에서 {result['total_count']}건 조회, {saved}건 신규 저장",
    }


@router.post("/collect-all")
async def collect_all_bids(
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """IT 컨설팅 공고 일괄 수집 (최근 24시간)"""
    background_tasks.add_task(run_batch_collect, db)
    return {"message": "IT 컨설팅 공고 일괄 수집을 시작합니다"}


@router.post("/{bid_id}/collect")
async def collect_bid(
    bid_id: int,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """특정 공고의 첨부파일 수집 + 변환 (사용자 수동 트리거)"""
    row = await db.fetchrow("SELECT id, status FROM bids WHERE id = $1", bid_id)
    if not row:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다")

    async def _collect_and_convert(bid_id, db):
        await run_collect_pipeline(bid_id, db)
        await run_convert(bid_id, db)

    await db.execute(
        "UPDATE bids SET status = 'collecting' WHERE id = $1", bid_id
    )
    background_tasks.add_task(_collect_and_convert, bid_id, db)

    return {"message": "첨부파일 수집 및 변환을 시작합니다", "bid_id": bid_id}


G2B_DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.g2b.go.kr/",
}


@router.get("/{bid_id}/attachments/{att_id}/download")
async def download_attachment(
    bid_id: int,
    att_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """첨부파일 다운로드 (나라장터 프록시)"""
    row = await db.fetchrow(
        "SELECT file_name, file_url FROM bid_attachments WHERE id = $1 AND bid_id = $2",
        att_id,
        bid_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다")

    file_url = row["file_url"]
    file_name = row["file_name"] or "download"

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(file_url, headers=G2B_DOWNLOAD_HEADERS)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="원본 파일 다운로드 실패")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="원본 파일 다운로드 실패")

    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    mime_map = {
        "hwp": "application/x-hwp", "hwpx": "application/x-hwpx",
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "zip": "application/zip",
    }
    content_type = mime_map.get(ext, "application/octet-stream")
    encoded_name = quote(file_name, safe="")

    return StreamingResponse(
        iter([resp.content]),
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            "Content-Length": str(len(resp.content)),
        },
    )
