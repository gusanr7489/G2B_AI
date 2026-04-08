from fastapi import APIRouter, Depends

from database import get_db
from dependencies import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_stats(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """전체 통계 (CEO용) — 상태별 집계 + 마감 임박"""
    # 상태별 건수
    status_counts = await db.fetch(
        """
        SELECT status, COUNT(*) as count
        FROM bid_targets
        GROUP BY status
        """
    )
    stats = {row["status"]: row["count"] for row in status_counts}

    # 총 수집 공고 수
    total_bids = await db.fetchval("SELECT COUNT(*) FROM bids")

    # 마감 임박 (D-7 이내)
    urgent = await db.fetch(
        """
        SELECT t.id, t.status, t.assignee_id, u.name as assignee_name,
               b.bid_ntce_nm, b.dminstt_nm, b.bid_close_dt,
               t.required_staff, t.estimated_cost, t.bid_estimate
        FROM bid_targets t
        JOIN bids b ON b.id = t.bid_id
        LEFT JOIN users u ON u.id = t.assignee_id
        WHERE b.bid_close_dt BETWEEN NOW() AND NOW() + INTERVAL '7 days'
        ORDER BY b.bid_close_dt ASC
        """
    )

    return {
        "total_bids": total_bids,
        "target_stats": stats,
        "urgent_targets": [dict(r) for r in urgent],
    }


@router.get("/my")
async def get_my_dashboard(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """내 담당 현황 (담당자용)"""
    targets = await db.fetch(
        """
        SELECT t.id, t.bid_id, t.status, t.required_staff,
               t.estimated_cost, t.bid_estimate, t.notes,
               b.bid_ntce_nm, b.dminstt_nm, b.bid_close_dt,
               a.risk_level
        FROM bid_targets t
        JOIN bids b ON b.id = t.bid_id
        LEFT JOIN analyses a ON a.bid_id = t.bid_id AND a.analysis_status = 'completed'
        WHERE t.assignee_id = $1
        ORDER BY b.bid_close_dt ASC
        """,
        user["id"],
    )

    return {
        "my_targets": [dict(r) for r in targets],
        "total": len(targets),
    }
