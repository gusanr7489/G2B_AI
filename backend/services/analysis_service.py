import asyncio
import json
import logging

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from config import get_settings
from prompts.rfp_analysis import SYSTEM_PROMPT, build_analysis_prompt
from services import progress_store

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

    # 1. 첨부파일 로드 (PDF 직접 전송 + HWP는 변환 후 텍스트)
    from services.hwp_service import download_and_convert

    pdf_atts = await db.fetch(
        """
        SELECT file_name, file_url
        FROM bid_attachments
        WHERE bid_id = $1 AND lower(file_type) = 'pdf'
        """,
        bid_id,
    )
    hwp_atts = await db.fetch(
        """
        SELECT id, file_name, file_url, converted_md
        FROM bid_attachments
        WHERE bid_id = $1 AND lower(file_type) IN ('hwp', 'hwpx')
        """,
        bid_id,
    )

    if not pdf_atts and not hwp_atts:
        raise ValueError("분석할 첨부파일이 없습니다")

    g2b_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.g2b.go.kr/",
    }

    content_parts = []

    progress_store.emit(bid_id, f"분석 대상: PDF {len(pdf_atts)}건, HWP {len(hwp_atts)}건")

    # PDF → 원본 바이트로 Gemini에 직접 전송
    for att in pdf_atts:
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
                resp = await http.get(att["file_url"], headers=g2b_headers)
                if resp.status_code == 200:
                    content_parts.append(types.Part.from_bytes(
                        data=resp.content,
                        mime_type="application/pdf",
                    ))
                    progress_store.emit(bid_id, f"PDF 다운로드: {att['file_name']} ({len(resp.content)//1024}KB)")
                    logger.info(f"PDF 다운로드 완료: {att['file_name']} ({len(resp.content)} bytes)")
        except Exception as e:
            progress_store.emit(bid_id, f"PDF 다운로드 실패: {att['file_name']}", level="warning")
            logger.warning(f"PDF 다운로드 에러 ({att['file_name']}): {e}")

    # HWP → 리브레AI 변환 후 텍스트로 전송
    for att in hwp_atts:
        text = att["converted_md"]
        if not text:
            # 아직 변환 안 된 HWP → 변환 실행
            try:
                result = await download_and_convert(att["file_url"], att["file_name"])
                text = result.get("md", "")
                if text:
                    await db.execute(
                        """
                        UPDATE bid_attachments
                        SET converted_html = $1, converted_md = $2, conversion_status = 'completed'
                        WHERE id = $3
                        """,
                        result.get("html", ""),
                        text,
                        att["id"],
                    )
                    logger.info(f"HWP 변환 완료: {att['file_name']}")
            except Exception as e:
                logger.warning(f"HWP 변환 실패 ({att['file_name']}): {e}")
        if text:
            content_parts.append(f"[파일: {att['file_name']}]\n{text}")

    if not content_parts:
        raise ValueError("분석 가능한 첨부파일이 없습니다")

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

    # 3. Gemini 호출 (429/503 재시도 + fallback 모델)
    import time as _time
    try:
        client = _get_client()
        prompt_text = build_analysis_prompt("")

        # 첨부파일 (PDF 바이트 + HWP 텍스트) + 프롬프트를 contents로 구성
        contents = content_parts + [prompt_text]

        gen_config = {
            "system_instruction": SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "temperature": 0.1,
        }

        # primary → fallback 순서로 시도
        models_to_try = [settings.gemini_model]
        if settings.gemini_fallback_model and settings.gemini_fallback_model != settings.gemini_model:
            models_to_try.append(settings.gemini_fallback_model)

        response = None
        actual_model = None
        last_error: Exception | None = None

        for model_name in models_to_try:
            progress_store.emit(bid_id, f"Gemini 호출 시작 (model={model_name})")
            _t0 = _time.monotonic()
            try:
                for attempt in range(3):
                    try:
                        # SDK sync 호출 → 이벤트 루프 차단 방지 위해 별도 스레드 실행
                        response = await asyncio.to_thread(
                            client.models.generate_content,
                            model=model_name,
                            contents=contents,
                            config=gen_config,
                        )
                        actual_model = model_name
                        elapsed = _time.monotonic() - _t0
                        progress_store.emit(bid_id, f"Gemini 응답 수신 ({elapsed:.1f}초, model={model_name})", level="success")
                        logger.info(f"Gemini 응답 성공: model={model_name} (bid_id={bid_id})")
                        break
                    except (genai_errors.ClientError, genai_errors.ServerError) as e:
                        err_str = str(e)
                        if ("429" in err_str or "503" in err_str) and attempt < 2:
                            wait = 20 * (attempt + 1)
                            progress_store.emit(bid_id, f"재시도 대기 {wait}초 (시도 {attempt + 1}/3)", level="warning")
                            logger.warning(f"Gemini 재시도 대기 {wait}초 (bid_id={bid_id}, model={model_name}, 시도 {attempt + 1}/3): {err_str[:50]}")
                            await asyncio.sleep(wait)
                        else:
                            raise
                if response is not None:
                    break
            except Exception as e:
                last_error = e
                if model_name != models_to_try[-1]:
                    progress_store.emit(bid_id, f"{model_name} 실패, fallback {models_to_try[-1]}로 전환", level="warning")
                    logger.warning(f"{model_name} 모든 재시도 실패, fallback 시도 (bid_id={bid_id}): {str(e)[:80]}")
                    response = None
                    continue
                else:
                    raise

        if response is None:
            raise last_error or RuntimeError("Gemini 응답 없음")

        progress_store.emit(bid_id, "Gemini 응답 JSON 파싱")
        result = _parse_json_response(response.text)

    except Exception as e:
        progress_store.emit(bid_id, f"Gemini 분석 실패: {str(e)[:120]}", level="error")
        logger.error(f"Gemini 분석 실패 (bid_id={bid_id}): {e}", exc_info=True)
        await db.execute(
            "UPDATE analyses SET analysis_status = 'failed' WHERE bid_id = $1",
            bid_id,
        )
        raise

    # 4. DB 저장
    basic = result.get("basic_info", {})
    poison = result.get("poison_clauses", {})

    # 추정가격/배정예산 숫자 변환
    def _to_int(val):
        if val is None:
            return None
        try:
            return int(float(str(val)))
        except (ValueError, TypeError):
            return None

    def _to_datetime(val):
        if val is None:
            return None
        if isinstance(val, str):
            from datetime import datetime
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    continue
        return None

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
            project_type = $13,
            project_duration = $14,
            estimated_price = $15,
            allocated_budget = $16,
            contract_method = $17,
            model_used = $18,
            analysis_status = 'completed'
        WHERE bid_id = $1
        """,
        bid_id,
        basic.get("issuing_org"),
        _to_datetime(basic.get("deadline")),
        basic.get("project_summary"),
        basic.get("project_scope"),
        json.dumps(result.get("eval_criteria", []), ensure_ascii=False),
        json.dumps(result.get("requirements", []), ensure_ascii=False),
        result.get("qualification"),
        json.dumps(result.get("tech_requirements", []), ensure_ascii=False),
        json.dumps(poison, ensure_ascii=False),
        poison.get("risk_level", "safe"),
        json.dumps(result, ensure_ascii=False),
        basic.get("project_type"),
        basic.get("project_duration"),
        _to_int(basic.get("estimated_price")),
        _to_int(basic.get("allocated_budget")),
        basic.get("contract_method"),
        actual_model,
    )

    progress_store.emit(bid_id, f"DB 저장 완료 (위험도={poison.get('risk_level', 'safe')})", level="success")
    logger.info(f"RFP 분석 완료: bid_id={bid_id}, risk_level={poison.get('risk_level')}")
    return result


# 제안목차 생성은 services/outline_service.py 로 이동.
