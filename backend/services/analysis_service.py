import json
import logging

from google import genai

from config import get_settings
from prompts.rfp_analysis import SYSTEM_PROMPT, build_analysis_prompt
from prompts.outline_generation import OUTLINE_SYSTEM_PROMPT, build_outline_prompt

logger = logging.getLogger(__name__)


def _get_client():
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _parse_json_response(text: str) -> dict:
    """Gemini 응답에서 JSON 추출 (```json ... ``` 블록 또는 순수 JSON)"""
    text = text.strip()
    if text.startswith("```"):
        # ```json ... ``` 블록 제거
        lines = text.split("\n")
        json_lines = []
        inside = False
        for line in lines:
            if line.strip().startswith("```") and not inside:
                inside = True
                continue
            elif line.strip() == "```" and inside:
                break
            elif inside:
                json_lines.append(line)
        text = "\n".join(json_lines)
    return json.loads(text)


async def analyze_rfp(bid_id: int, db) -> dict:
    """
    공고의 첨부파일 텍스트를 로드 → Gemini 호출 → 분석 결과 파싱 → DB 저장.
    """
    settings = get_settings()

    # 1. 첨부파일 텍스트 로드 (MD 우선, 없으면 HTML)
    attachments = await db.fetch(
        """
        SELECT converted_md, converted_html
        FROM bid_attachments
        WHERE bid_id = $1 AND conversion_status = 'completed'
        """,
        bid_id,
    )

    rfp_text = ""
    for att in attachments:
        text = att["converted_md"] or att["converted_html"] or ""
        if text:
            rfp_text += text + "\n\n"

    if not rfp_text.strip():
        raise ValueError("분석할 첨부파일 텍스트가 없습니다")

    # 텍스트 길이 제한 (Gemini 입력 한도 고려)
    max_chars = 500_000
    if len(rfp_text) > max_chars:
        rfp_text = rfp_text[:max_chars]

    # 2. 분석 상태 업데이트 (기존 레코드 있으면 업데이트, 없으면 삽입)
    existing = await db.fetchrow(
        "SELECT id FROM analyses WHERE bid_id = $1", bid_id
    )
    if existing:
        await db.execute(
            "UPDATE analyses SET analysis_status = 'processing' WHERE bid_id = $1",
            bid_id,
        )
    else:
        await db.execute(
            "INSERT INTO analyses (bid_id, analysis_status) VALUES ($1, 'processing')",
            bid_id,
        )

    # 3. Gemini 호출
    try:
        client = _get_client()
        prompt = build_analysis_prompt(rfp_text)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )

        result = _parse_json_response(response.text)

    except Exception as e:
        logger.error(f"Gemini 분석 실패 (bid_id={bid_id}): {e}", exc_info=True)
        await db.execute(
            "UPDATE analyses SET analysis_status = 'failed' WHERE bid_id = $1",
            bid_id,
        )
        raise

    # 4. DB 저장
    basic = result.get("basic_info", {})
    poison = result.get("poison_clauses", {})

    await db.execute(
        """
        UPDATE analyses SET
            issuing_org = $2,
            deadline = $3,
            project_summary = $4,
            project_scope = $5,
            eval_criteria = $6,
            requirements = $7,
            qualification = $8,
            tech_requirements = $9,
            poison_clauses = $10,
            risk_level = $11,
            raw_analysis = $12,
            analysis_status = 'completed'
        WHERE bid_id = $1
        """,
        bid_id,
        basic.get("issuing_org"),
        basic.get("deadline"),
        basic.get("project_summary"),
        basic.get("project_scope"),
        json.dumps(result.get("eval_criteria", []), ensure_ascii=False),
        json.dumps(result.get("requirements", []), ensure_ascii=False),
        result.get("qualification"),
        json.dumps(result.get("tech_requirements", []), ensure_ascii=False),
        json.dumps(poison, ensure_ascii=False),
        poison.get("risk_level", "safe"),
        json.dumps(result, ensure_ascii=False),
    )

    logger.info(f"RFP 분석 완료: bid_id={bid_id}, risk_level={poison.get('risk_level')}")
    return result


async def generate_outline(analysis_id: int, db) -> dict:
    """
    분석 결과 기반 제안목차 생성 (수동 트리거).
    """
    settings = get_settings()

    # 1. 분석 결과 로드
    analysis = await db.fetchrow(
        """
        SELECT id, bid_id, project_summary, project_scope,
               eval_criteria, requirements, raw_analysis
        FROM analyses WHERE id = $1 AND analysis_status = 'completed'
        """,
        analysis_id,
    )
    if not analysis:
        raise ValueError("완료된 분석 결과를 찾을 수 없습니다")

    analysis_data = {}
    raw = analysis["raw_analysis"]
    if isinstance(raw, str):
        analysis_data = json.loads(raw)
    elif isinstance(raw, dict):
        analysis_data = raw

    # ISP/ISMP 판별 (프로젝트 요약에서 키워드 확인)
    summary = (analysis_data.get("basic_info", {}).get("project_summary", "") or "").lower()
    is_ismp = "ismp" in summary or "마스터플랜" in summary

    # 2. Gemini 호출
    client = _get_client()
    prompt = build_outline_prompt(analysis_data, is_ismp)

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config={
            "system_instruction": OUTLINE_SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    )

    result = _parse_json_response(response.text)

    # 3. DB 저장 (기존 있으면 업데이트)
    existing_outline = await db.fetchrow(
        "SELECT id FROM proposal_outlines WHERE analysis_id = $1", analysis_id
    )
    outline_json = json.dumps(result, ensure_ascii=False)
    if existing_outline:
        await db.execute(
            "UPDATE proposal_outlines SET outline_data = $1, is_ismp = $2, updated_at = NOW() WHERE analysis_id = $3",
            outline_json, is_ismp, analysis_id,
        )
    else:
        await db.execute(
            "INSERT INTO proposal_outlines (analysis_id, outline_data, is_ismp) VALUES ($1, $2, $3)",
            analysis_id, outline_json, is_ismp,
        )

    logger.info(f"제안목차 생성 완료: analysis_id={analysis_id}, is_ismp={is_ismp}")
    return result
