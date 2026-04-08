from fastapi import APIRouter, Depends, HTTPException, Query

from database import get_db
from dependencies import get_current_user
from schemas.target import TargetCreate, TargetResponse, TargetUpdate

router = APIRouter()


@router.post("", response_model=TargetResponse, status_code=201)
async def create_target(
    body: TargetCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """공고를 대상 리스트로 이동"""
    bid = await db.fetchrow("SELECT id FROM bids WHERE id = $1", body.bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다")

    existing = await db.fetchrow(
        "SELECT id FROM bid_targets WHERE bid_id = $1", body.bid_id
    )
    if existing:
        raise HTTPException(status_code=409, detail="이미 대상에 추가된 공고입니다")

    row = await db.fetchrow(
        """
        INSERT INTO bid_targets (bid_id, assignee_id, status)
        VALUES ($1, $2, '검토필요')
        RETURNING id, bid_id, assignee_id, status, required_staff,
                  office_info, estimated_cost, bid_estimate, notes,
                  created_at, updated_at
        """,
        body.bid_id,
        user["id"],
    )
    return await _enrich_target(dict(row), db)


@router.get("", response_model=list[TargetResponse])
async def list_targets(
    status: str = Query("", description="상태 필터"),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """대상 리스트 조회"""
    if status:
        rows = await db.fetch(
            """
            SELECT t.* FROM bid_targets t
            WHERE t.status = $1
            ORDER BY t.updated_at DESC
            """,
            status,
        )
    else:
        rows = await db.fetch(
            "SELECT * FROM bid_targets ORDER BY updated_at DESC"
        )

    results = []
    for row in rows:
        enriched = await _enrich_target(dict(row), db)
        results.append(enriched)
    return results


@router.patch("/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: int,
    body: TargetUpdate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """대상 정보 수정 (상태, 인원, 비용 등)"""
    existing = await db.fetchrow(
        "SELECT id FROM bid_targets WHERE id = $1", target_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="대상을 찾을 수 없습니다")

    updates = []
    params = []
    idx = 1

    for field, value in body.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = ${idx}")
        params.append(value)
        idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="수정할 항목이 없습니다")

    updates.append(f"updated_at = NOW()")
    params.append(target_id)

    row = await db.fetchrow(
        f"""
        UPDATE bid_targets SET {', '.join(updates)}
        WHERE id = ${idx}
        RETURNING id, bid_id, assignee_id, status, required_staff,
                  office_info, estimated_cost, bid_estimate, notes,
                  created_at, updated_at
        """,
        *params,
    )
    return await _enrich_target(dict(row), db)


@router.delete("/{target_id}")
async def delete_target(
    target_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """대상에서 제거"""
    result = await db.execute(
        "DELETE FROM bid_targets WHERE id = $1", target_id
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="대상을 찾을 수 없습니다")
    return {"message": "삭제 완료"}


async def _enrich_target(target: dict, db) -> TargetResponse:
    """대상에 공고명, 기관, 마감일, 위험도, 담당자명 조인"""
    bid = await db.fetchrow(
        "SELECT bid_ntce_nm, dminstt_nm, bid_close_dt FROM bids WHERE id = $1",
        target["bid_id"],
    )
    analysis = await db.fetchrow(
        "SELECT risk_level FROM analyses WHERE bid_id = $1 AND analysis_status = 'completed' ORDER BY created_at DESC LIMIT 1",
        target["bid_id"],
    )
    assignee = None
    if target.get("assignee_id"):
        assignee = await db.fetchrow(
            "SELECT name FROM users WHERE id = $1", target["assignee_id"]
        )

    return TargetResponse(
        **target,
        bid_ntce_nm=bid["bid_ntce_nm"] if bid else None,
        dminstt_nm=bid["dminstt_nm"] if bid else None,
        bid_close_dt=bid["bid_close_dt"] if bid else None,
        risk_level=analysis["risk_level"] if analysis else None,
        assignee_name=assignee["name"] if assignee else None,
    )
