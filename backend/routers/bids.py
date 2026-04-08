import json
from fastapi import APIRouter, Depends, HTTPException, Query

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

router = APIRouter()


@router.get("", response_model=BidListResponse)
async def list_bids(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="공고명 검색"),
    status: str = Query("", description="상태 필터 (new/processing/completed/failed)"),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """DB에 수집된 공고 목록 조회 (페이지네이션, 필터)"""
    conditions = []
    params = []
    idx = 1

    if keyword:
        conditions.append(f"bid_ntce_nm ILIKE ${idx}")
        params.append(f"%{keyword}%")
        idx += 1

    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = await db.fetchval(
        f"SELECT COUNT(*) FROM bids {where}", *params
    )

    offset = (page - 1) * size
    rows = await db.fetch(
        f"""
        SELECT id, bid_ntce_no, bid_ntce_ord, bid_ntce_nm,
               ntce_instt_nm, dminstt_nm, bid_close_dt,
               asign_bdgt_amt, presmpt_prce, status, created_at
        FROM bids {where}
        ORDER BY created_at DESC
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


@router.post("/{bid_id}/collect")
async def collect_bid(
    bid_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """특정 공고의 첨부파일 수집 트리거 (Phase 3에서 HWP 변환 연결)"""
    row = await db.fetchrow("SELECT id, status FROM bids WHERE id = $1", bid_id)
    if not row:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다")

    # Phase 3에서 HWP 변환 파이프라인 연결 예정
    await db.execute(
        "UPDATE bids SET status = 'processing' WHERE id = $1", bid_id
    )

    return {"message": "수집 시작 (HWP 변환은 Phase 3에서 연결)", "bid_id": bid_id}
