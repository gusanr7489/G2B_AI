import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

# 나라장터 용역 공고 목록 조회 API
G2B_BID_LIST_URL = (
    "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
    "/getBidPblancListInfoServc"
)

KST = timezone(timedelta(hours=9))


def _fmt_dt(dt: datetime) -> str:
    """datetime → YYYYMMDDHHmm (12자리)"""
    return dt.strftime("%Y%m%d%H%M")


async def search_bids(
    keyword: str = "",
    inqry_bgn_dt: str = "",
    inqry_end_dt: str = "",
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict:
    """나라장터 용역 공고 목록 검색 (재시도 3회)"""
    settings = get_settings()

    if not inqry_bgn_dt:
        now = datetime.now(KST)
        inqry_bgn_dt = _fmt_dt(now - timedelta(hours=12))
    if not inqry_end_dt:
        inqry_end_dt = _fmt_dt(datetime.now(KST))

    params = {
        "serviceKey": settings.g2b_api_key,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "inqryDiv": 1,
        "inqryBgnDt": inqry_bgn_dt,
        "inqryEndDt": inqry_end_dt,
        "type": "json",
    }
    if keyword:
        params["bidNtceNm"] = keyword

    last_err = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(G2B_BID_LIST_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

                # 응답 구조 파싱
                body = data.get("response", {}).get("body", {})
                items = body.get("items", "")
                if not items or items == "":
                    return {"items": [], "total_count": 0}

                item_list = items if isinstance(items, list) else items.get("item", [])
                if isinstance(item_list, dict):
                    item_list = [item_list]

                total = int(body.get("totalCount", len(item_list)))
                return {"items": item_list, "total_count": total}

        except Exception as e:
            last_err = e
            logger.warning(f"나라장터 API 호출 실패 (시도 {attempt + 1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    logger.error(f"나라장터 API 호출 최종 실패: {last_err}")
    raise last_err


def parse_bid_item(item: dict) -> dict:
    """나라장터 API 응답 항목 → DB 저장 형식 변환"""
    close_dt = None
    raw_close = item.get("bidClseDt") or item.get("bidNtceClseDt")
    if raw_close:
        try:
            # YYYYMMDDHHmm 또는 YYYY-MM-DD HH:mm:ss
            clean = raw_close.replace("-", "").replace(":", "").replace(" ", "").replace("T", "")
            close_dt = datetime.strptime(clean[:12], "%Y%m%d%H%M")
        except (ValueError, IndexError):
            pass

    def _int_or_none(val):
        if val is None or val == "":
            return None
        try:
            return int(float(str(val)))
        except (ValueError, TypeError):
            return None

    return {
        "bid_ntce_no": item.get("bidNtceNo", ""),
        "bid_ntce_ord": item.get("bidNtceOrd", "00"),
        "bid_ntce_nm": item.get("bidNtceNm", ""),
        "ntce_instt_nm": item.get("ntceInsttNm", ""),
        "dminstt_nm": item.get("dminsttNm", ""),
        "bid_close_dt": close_dt,
        "asign_bdgt_amt": _int_or_none(item.get("asignBdgtAmt")),
        "presmpt_prce": _int_or_none(item.get("presmptPrce")),
        "bid_ntce_url": item.get("bidNtceDtlUrl", ""),
        "raw_data": json.dumps(item, ensure_ascii=False),
    }


async def save_bids_to_db(db, items: list[dict]) -> int:
    """파싱된 공고 목록을 DB에 저장 (중복 무시). 저장된 건수 반환."""
    saved = 0
    for item in items:
        parsed = parse_bid_item(item)
        try:
            await db.execute(
                """
                INSERT INTO bids (
                    bid_ntce_no, bid_ntce_ord, bid_ntce_nm,
                    ntce_instt_nm, dminstt_nm, bid_close_dt,
                    asign_bdgt_amt, presmpt_prce, bid_ntce_url, raw_data
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (bid_ntce_no, bid_ntce_ord) DO NOTHING
                """,
                parsed["bid_ntce_no"],
                parsed["bid_ntce_ord"],
                parsed["bid_ntce_nm"],
                parsed["ntce_instt_nm"],
                parsed["dminstt_nm"],
                parsed["bid_close_dt"],
                parsed["asign_bdgt_amt"],
                parsed["presmpt_prce"],
                parsed["bid_ntce_url"],
                parsed["raw_data"],
            )
            saved += 1
        except Exception as e:
            logger.warning(f"공고 저장 실패 ({parsed['bid_ntce_no']}): {e}")
    return saved
