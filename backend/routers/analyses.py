import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from database import get_db
from dependencies import get_current_user
from schemas.analysis import AnalysisResponse, AnalysisStatusResponse, OutlineResponse
from services.analysis_service import analyze_rfp, generate_outline

router = APIRouter()


@router.post("/{bid_id}")
async def request_analysis(
    bid_id: int,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """AI 분석 요청 (비동기 처리)"""
    bid = await db.fetchrow("SELECT id FROM bids WHERE id = $1", bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다")

    # 이미 진행 중인 분석 확인
    existing = await db.fetchrow(
        "SELECT analysis_status FROM analyses WHERE bid_id = $1", bid_id
    )
    if existing and existing["analysis_status"] == "processing":
        return {"message": "분석이 이미 진행 중입니다", "bid_id": bid_id}

    background_tasks.add_task(analyze_rfp, bid_id, db)
    return {"message": "AI 분석을 시작합니다", "bid_id": bid_id}


@router.get("/{bid_id}", response_model=AnalysisResponse)
async def get_analysis(
    bid_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """분석 결과 조회"""
    row = await db.fetchrow(
        """
        SELECT id, bid_id, issuing_org, deadline, project_summary,
               project_scope, eval_criteria, requirements, qualification,
               tech_requirements, poison_clauses, risk_level,
               analysis_status, created_at
        FROM analyses WHERE bid_id = $1
        ORDER BY created_at DESC LIMIT 1
        """,
        bid_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다")

    data = dict(row)
    # asyncpg JSONB → dict 변환
    for field in ["eval_criteria", "requirements", "tech_requirements", "poison_clauses"]:
        if isinstance(data.get(field), str):
            data[field] = json.loads(data[field])

    return AnalysisResponse(**data)


@router.get("/{bid_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    bid_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """분석 진행 상태 확인"""
    row = await db.fetchrow(
        "SELECT analysis_status, risk_level FROM analyses WHERE bid_id = $1 ORDER BY created_at DESC LIMIT 1",
        bid_id,
    )
    if not row:
        return AnalysisStatusResponse(bid_id=bid_id, analysis_status="none")

    return AnalysisStatusResponse(
        bid_id=bid_id,
        analysis_status=row["analysis_status"],
        risk_level=row["risk_level"],
    )


@router.post("/{bid_id}/outline")
async def request_outline(
    bid_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """제안목차 생성 (수동 트리거)"""
    analysis = await db.fetchrow(
        "SELECT id FROM analyses WHERE bid_id = $1 AND analysis_status = 'completed' ORDER BY created_at DESC LIMIT 1",
        bid_id,
    )
    if not analysis:
        raise HTTPException(
            status_code=400, detail="완료된 분석 결과가 없습니다. 먼저 AI 분석을 실행하세요."
        )

    result = await generate_outline(analysis["id"], db)
    return {"message": "제안목차 생성 완료", "bid_id": bid_id, "outline": result}


@router.get("/{bid_id}/outline", response_model=OutlineResponse)
async def get_outline(
    bid_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """생성된 제안목차 조회"""
    row = await db.fetchrow(
        """
        SELECT po.id, po.analysis_id, po.outline_data, po.is_ismp,
               po.created_at, po.updated_at
        FROM proposal_outlines po
        JOIN analyses a ON a.id = po.analysis_id
        WHERE a.bid_id = $1
        ORDER BY po.created_at DESC LIMIT 1
        """,
        bid_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="생성된 제안목차가 없습니다")

    data = dict(row)
    if isinstance(data.get("outline_data"), str):
        data["outline_data"] = json.loads(data["outline_data"])

    return OutlineResponse(**data)
