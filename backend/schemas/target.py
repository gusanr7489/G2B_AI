from pydantic import BaseModel
from datetime import datetime


# --- Request ---

class TargetCreate(BaseModel):
    bid_id: int


class TargetUpdate(BaseModel):
    status: str | None = None
    assignee_id: int | None = None
    required_staff: int | None = None
    office_info: str | None = None
    estimated_cost: int | None = None
    bid_estimate: int | None = None
    notes: str | None = None


# --- Response ---

class TargetResponse(BaseModel):
    id: int
    bid_id: int
    assignee_id: int | None
    assignee_name: str | None = None
    status: str
    required_staff: int | None
    office_info: str | None
    estimated_cost: int | None
    bid_estimate: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    # 공고 정보 조인
    bid_ntce_nm: str | None = None
    dminstt_nm: str | None = None
    bid_close_dt: datetime | None = None
    presmpt_prce: int | None = None
    risk_level: str | None = None
    analysis_status: str | None = None
