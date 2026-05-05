import json
import logging
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from database import get_db
from dependencies import get_current_user
from schemas.analysis import AnalysisResponse, AnalysisStatusResponse, OutlineResponse
from services.analysis_service import analyze_rfp
from services.collect_pipeline import run_collect_pipeline, run_convert
from services.g2b_service import fetch_eorder_attachments, save_attachments_to_db
from services import progress_store
from services.outline_service import (
    UnsupportedProjectTypeError,
    build_outline_xlsx,
    generate_outline as run_generate_outline,
)
from services.outline_types import is_supported, supported_types

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/outline/supported-types")
async def get_supported_outline_types(user=Depends(get_current_user)):
    """프론트가 어떤 사업 유형의 목차 생성을 지원하는지 알기 위해 호출."""
    return supported_types()


async def _collect_convert_and_analyze(bid_id: int, db):
    """첨부파일 수집 + 제안요청서 수집 → 변환 → AI 분석을 순차 실행"""
    import json
    import logging
    logger = logging.getLogger(__name__)

    try:
        # 1. 기본 첨부파일 수집 (공고서 등)
        att_count = await db.fetchval(
            "SELECT COUNT(*) FROM bid_attachments WHERE bid_id = $1", bid_id
        )
        if att_count == 0:
            progress_store.emit(bid_id, "첨부파일 수집 시작")
            logger.info(f"첨부파일 수집 시작: bid_id={bid_id}")
            await run_collect_pipeline(bid_id, db)
            progress_store.emit(bid_id, "첨부파일 수집 완료")
        else:
            progress_store.emit(bid_id, f"기존 첨부파일 {att_count}건 사용")

        # 2. 제안요청서 파일 수집 (e발주 20번 API)
        progress_store.emit(bid_id, "제안요청서(e발주) 조회")
        bid = await db.fetchrow(
            "SELECT bid_ntce_no, raw_data FROM bids WHERE id = $1", bid_id
        )
        if bid and bid["bid_ntce_no"]:
            raw = bid["raw_data"]
            if isinstance(raw, str):
                raw = json.loads(raw)
            bid_ntce_dt = (raw or {}).get("bidNtceDt", "")

            eorder_atts = await fetch_eorder_attachments(bid["bid_ntce_no"], bid_ntce_dt)
            if eorder_atts:
                await save_attachments_to_db(db, bid_id, eorder_atts)
                # PDF는 변환 완료 처리
                await db.execute(
                    """
                    UPDATE bid_attachments SET conversion_status = 'completed'
                    WHERE bid_id = $1 AND lower(file_type) = 'pdf'
                      AND conversion_status = 'pending'
                    """,
                    bid_id,
                )
                progress_store.emit(bid_id, f"제안요청서 {len(eorder_atts)}건 추가")
                logger.info(f"제안요청서 {len(eorder_atts)}건 추가: bid_id={bid_id}")
            else:
                progress_store.emit(bid_id, "제안요청서 추가 없음")

        # 3. 변환 (HWP → 리브레AI)
        converted_count = await db.fetchval(
            "SELECT COUNT(*) FROM bid_attachments WHERE bid_id = $1 AND conversion_status = 'completed'",
            bid_id,
        )
        if converted_count == 0:
            progress_store.emit(bid_id, "HWP→텍스트 변환 시작")
            logger.info(f"첨부파일 변환 시작: bid_id={bid_id}")
            await run_convert(bid_id, db)
            progress_store.emit(bid_id, "HWP→텍스트 변환 완료")
        else:
            progress_store.emit(bid_id, f"변환 완료된 파일 {converted_count}건 사용")

        # 4. AI 분석
        await analyze_rfp(bid_id, db)
        progress_store.emit(bid_id, "전체 파이프라인 완료", level="success")
    except Exception as e:
        progress_store.emit(bid_id, f"파이프라인 실패: {e}", level="error")
        logger.error(f"수집/변환/분석 파이프라인 실패 (bid_id={bid_id}): {e}", exc_info=True)


@router.post("/{bid_id}")
async def request_analysis(
    bid_id: int,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """AI 분석 요청 (첨부파일 수집 + 변환 + 분석을 자동 실행)"""
    bid = await db.fetchrow("SELECT id FROM bids WHERE id = $1", bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다")

    # 이미 진행 중인 분석 확인
    existing = await db.fetchrow(
        "SELECT analysis_status FROM analyses WHERE bid_id = $1", bid_id
    )
    if existing and existing["analysis_status"] == "processing":
        return {"message": "분석이 이미 진행 중입니다", "bid_id": bid_id}

    # 기존 결과(완료/실패/기타)가 있으면 삭제 후 재분석 (proposal_outlines는 CASCADE)
    if existing:
        await db.execute("DELETE FROM analyses WHERE bid_id = $1", bid_id)

    progress_store.clear(bid_id)
    progress_store.emit(bid_id, "AI 분석 요청 접수")
    background_tasks.add_task(_collect_convert_and_analyze, bid_id, db)
    return {"message": "첨부파일 수집 및 AI 분석을 시작합니다", "bid_id": bid_id}


@router.delete("/{bid_id}", status_code=204)
async def delete_analysis(
    bid_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """분석 결과 삭제 (proposal_outlines는 CASCADE)"""
    existing = await db.fetchrow(
        "SELECT analysis_status FROM analyses WHERE bid_id = $1", bid_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다")
    if existing["analysis_status"] == "processing":
        raise HTTPException(status_code=409, detail="진행 중인 분석은 삭제할 수 없습니다")
    await db.execute("DELETE FROM analyses WHERE bid_id = $1", bid_id)


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
               project_type, project_duration, estimated_price,
               allocated_budget, contract_method,
               model_used, analysis_status, created_at
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
    logs = progress_store.get(bid_id)
    if not row:
        return AnalysisStatusResponse(bid_id=bid_id, analysis_status="none", logs=logs)

    return AnalysisStatusResponse(
        bid_id=bid_id,
        analysis_status=row["analysis_status"],
        risk_level=row["risk_level"],
        logs=logs,
    )


@router.post("/{bid_id}/outline")
async def request_outline(
    bid_id: int,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """제안목차 생성 (백그라운드, 진행 로그는 progress_store)."""
    analysis = await db.fetchrow(
        """
        SELECT id, project_type FROM analyses
        WHERE bid_id = $1 AND analysis_status = 'completed'
        ORDER BY created_at DESC LIMIT 1
        """,
        bid_id,
    )
    if not analysis:
        raise HTTPException(
            status_code=400,
            detail="완료된 분석 결과가 없습니다. 먼저 AI 분석을 실행하세요.",
        )
    if not is_supported(analysis["project_type"]):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{analysis['project_type'] or '미정'} 유형은 목차 생성을 지원하지 않습니다"
            ),
        )

    progress_store.clear(bid_id)
    progress_store.emit(bid_id, "목차 생성 요청 접수")
    background_tasks.add_task(_run_outline_task, bid_id, db)
    return {"message": "제안목차 생성을 시작합니다", "bid_id": bid_id}


async def _run_outline_task(bid_id: int, db) -> None:
    try:
        await run_generate_outline(bid_id, db)
    except UnsupportedProjectTypeError:
        # 사용자에게 보일 메시지는 progress_store에 이미 emit됨
        pass
    except Exception as e:  # noqa: BLE001
        progress_store.emit(bid_id, f"목차 생성 실패: {str(e)[:120]}", level="error")
        logger.error(f"목차 생성 실패 (bid_id={bid_id}): {e}", exc_info=True)


@router.get("/{bid_id}/outline/excel")
async def download_outline_excel(
    bid_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """제안목차 xlsx 다운로드."""
    row = await db.fetchrow(
        """
        SELECT po.outline_data, b.bid_ntce_nm
        FROM proposal_outlines po
        JOIN analyses a ON a.id = po.analysis_id
        JOIN bids b ON b.id = a.bid_id
        WHERE a.bid_id = $1
        ORDER BY po.created_at DESC LIMIT 1
        """,
        bid_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="생성된 제안목차가 없습니다")

    raw = row["outline_data"]
    if isinstance(raw, str):
        raw = json.loads(raw)

    xlsx_bytes = build_outline_xlsx(raw)
    bid_name = row["bid_ntce_nm"] or "outline"
    filename = f"(제안목차) {bid_name}.xlsx"
    encoded = quote(filename, safe="")

    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "Content-Length": str(len(xlsx_bytes)),
        },
    )


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
