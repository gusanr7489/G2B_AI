import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

# 나라장터 검색조건에 의한 입찰공고 용역 조회 API (키워드 검색 지원)
G2B_BID_LIST_URL = (
    "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
    "/getBidPblancListInfoServcPPSSrch"
)

# 나라장터 전자입찰 첨부파일 조회 API (제안요청서 등 상세 파일)
G2B_ATCH_FILE_URL = (
    "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
    "/getBidPblancListInfoEorderAtchFileInfo"
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


async def fetch_eorder_attachments(bid_ntce_no: str, bid_ntce_dt: str = "") -> list[dict]:
    """20번 API로 전자입찰 첨부파일(제안요청서 등) 조회.
    bid_ntce_dt: 공고일자 (YYYYMMDD). 날짜 범위 검색에 사용.

    이 API는 bidNtceNo 파라미터를 지원하지 않으므로
    날짜 범위를 좁혀서 전체 페이지를 탐색하며 공고번호를 매칭한다.
    """
    settings = get_settings()

    # 공고일 당일로 좁게 검색 (결과 수 최소화)
    # bid_ntce_dt는 "YYYYMMDD" 또는 "YYYY-MM-DD HH:mm:ss" 형식
    if bid_ntce_dt and len(bid_ntce_dt) >= 8:
        clean_dt = bid_ntce_dt.replace("-", "").replace(" ", "").replace(":", "").replace("T", "")[:8]
        bgn = clean_dt + "0000"
        end = clean_dt + "2359"
    else:
        now = datetime.now(KST)
        bgn = now.strftime("%Y%m%d") + "0000"
        end = now.strftime("%Y%m%d") + "2359"

    result = []
    total_count = None
    for page in range(1, 50):
        params = {
            "serviceKey": settings.g2b_api_key,
            "pageNo": page,
            "numOfRows": 100,
            "inqryDiv": 1,
            "inqryBgnDt": bgn,
            "inqryEndDt": end,
            "type": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(G2B_ATCH_FILE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                body = data.get("response", {}).get("body", {})

                if total_count is None:
                    total_count = int(body.get("totalCount", 0))
                    logger.info(f"e발주 첨부파일 검색: {total_count}건 ({bgn}~{end}), 공고번호={bid_ntce_no}")

                items = body.get("items", "")
                if not items:
                    break
                item_list = items if isinstance(items, list) else items.get("item", [])
                if isinstance(item_list, dict):
                    item_list = [item_list]

                for item in item_list:
                    if item.get("bidNtceNo") == bid_ntce_no:
                        name = item.get("eorderAtchFileNm", "")
                        url = item.get("eorderAtchFileUrl", "")
                        if name and url:
                            ext = name.rsplit(".", 1)[-1].lower() if "." in name else "unknown"
                            result.append({
                                "file_name": name,
                                "file_url": url,
                                "file_type": ext,
                            })

                # 찾았으면 끝
                if result:
                    break
                # 마지막 페이지
                if len(item_list) < 100:
                    break
        except Exception as e:
            logger.warning(f"e발주 첨부파일 API 호출 실패 (page {page}): {e}")
            break

    logger.info(f"e발주 첨부파일 결과: {len(result)}건 (공고번호={bid_ntce_no})")
    return result


def extract_attachments_from_raw(raw_data: dict | str | None) -> list[dict]:
    """raw_data(나라장터 API 원본)에서 첨부파일 URL/파일명 추출.
    ntceSpecDocUrl1~10, ntceSpecFileNm1~10 필드 사용."""
    if not raw_data:
        return []
    if isinstance(raw_data, str):
        raw_data = json.loads(raw_data)

    result = []
    for i in range(1, 11):
        url = raw_data.get(f"ntceSpecDocUrl{i}", "")
        name = raw_data.get(f"ntceSpecFileNm{i}", "")
        if not url or not name:
            continue
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else "unknown"
        result.append({
            "file_name": name,
            "file_url": url,
            "file_type": ext,
        })
    return result


async def save_attachments_to_db(db, bid_id: int, attachments: list[dict]) -> int:
    """첨부파일 정보를 DB에 저장 (중복 무시). 저장된 건수 반환."""
    saved = 0
    for att in attachments:
        try:
            await db.execute(
                """
                INSERT INTO bid_attachments (bid_id, file_name, file_type, file_url)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (bid_id, file_name) DO NOTHING
                """,
                bid_id,
                att["file_name"],
                att["file_type"],
                att["file_url"],
            )
            saved += 1
        except Exception as e:
            logger.warning(f"첨부파일 저장 실패 ({att['file_name']}): {e}")
    return saved


async def save_bids_to_db(db, items: list[dict], filter_it: bool = True) -> int:
    """파싱된 공고 목록을 DB에 저장 + 첨부파일 URL 자동 수집. 저장된 건수 반환."""
    from services.scheduler_service import is_it_consulting_bid

    saved = 0
    for item in items:
        parsed = parse_bid_item(item)
        if filter_it and not is_it_consulting_bid(parsed["bid_ntce_nm"]):
            continue
        try:
            result = await db.execute(
                """
                INSERT INTO bids (
                    bid_ntce_no, bid_ntce_ord, bid_ntce_nm,
                    ntce_instt_nm, dminstt_nm, bid_close_dt,
                    asign_bdgt_amt, presmpt_prce, bid_ntce_url, raw_data,
                    status
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
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
                "collected",
            )

            if result == "INSERT 0 1":
                saved += 1
                # 신규 저장된 공고의 첨부파일 URL 자동 수집
                bid_id = await db.fetchval(
                    "SELECT id FROM bids WHERE bid_ntce_no = $1 AND bid_ntce_ord = $2",
                    parsed["bid_ntce_no"],
                    parsed["bid_ntce_ord"],
                )
                if bid_id:
                    # 1) raw_data에서 ntceSpecDocUrl 추출
                    attachments = extract_attachments_from_raw(parsed["raw_data"])
                    # 2) 20번 API에서 전자입찰 첨부파일 (제안요청서 등) 추가
                    bid_ntce_dt = item.get("bidNtceDt", "")
                    try:
                        eorder_atts = await fetch_eorder_attachments(
                            parsed["bid_ntce_no"], bid_ntce_dt
                        )
                        # 중복 파일명 제거
                        existing_names = {a["file_name"] for a in attachments}
                        for ea in eorder_atts:
                            if ea["file_name"] not in existing_names:
                                attachments.append(ea)
                    except Exception as e:
                        logger.warning(f"전자입찰 첨부파일 조회 실패 ({parsed['bid_ntce_no']}): {e}")

                    if attachments:
                        await save_attachments_to_db(db, bid_id, attachments)
                        # PDF는 변환 불필요 → completed
                        await db.execute(
                            """
                            UPDATE bid_attachments SET conversion_status = 'completed'
                            WHERE bid_id = $1 AND lower(file_type) = 'pdf'
                              AND conversion_status = 'pending'
                            """,
                            bid_id,
                        )
                        await db.execute(
                            "UPDATE bids SET status = 'completed' WHERE id = $1", bid_id
                        )
                    else:
                        await db.execute(
                            "UPDATE bids SET status = 'no_file' WHERE id = $1", bid_id
                        )

        except Exception as e:
            logger.warning(f"공고 저장 실패 ({parsed['bid_ntce_no']}): {e}")
    return saved
