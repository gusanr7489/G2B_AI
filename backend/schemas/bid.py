from pydantic import BaseModel
from datetime import datetime


# --- Request ---

class BidSearchParams(BaseModel):
    keyword: str = ""
    inqry_bgn_dt: str = ""  # YYYYMMDDHHmm
    inqry_end_dt: str = ""  # YYYYMMDDHHmm
    page_no: int = 1
    num_of_rows: int = 100


class BidCollectRequest(BaseModel):
    bid_ntce_no: str
    bid_ntce_ord: str = "00"


# --- Response ---

class BidSummary(BaseModel):
    id: int
    bid_ntce_no: str
    bid_ntce_ord: str | None
    bid_ntce_nm: str
    ntce_instt_nm: str | None
    dminstt_nm: str | None
    bid_close_dt: datetime | None
    asign_bdgt_amt: int | None
    presmpt_prce: int | None
    status: str
    created_at: datetime


class BidDetail(BaseModel):
    id: int
    bid_ntce_no: str
    bid_ntce_ord: str | None
    bid_ntce_nm: str
    ntce_instt_nm: str | None
    dminstt_nm: str | None
    bid_close_dt: datetime | None
    asign_bdgt_amt: int | None
    presmpt_prce: int | None
    bid_ntce_url: str | None
    raw_data: dict | None
    status: str
    created_at: datetime
    attachments: list[dict] = []


class BidListResponse(BaseModel):
    items: list[BidSummary]
    total: int
    page: int
    size: int
