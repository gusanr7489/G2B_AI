from pydantic import BaseModel
from datetime import datetime


class PoisonClause(BaseModel):
    category: str
    clause: str
    severity: str  # safe / caution / warning / danger
    reason: str
    source: str = ""


class PoisonClausesResult(BaseModel):
    items: list[PoisonClause] = []
    risk_level: str = "safe"
    summary: str = ""


class AnalysisResponse(BaseModel):
    id: int
    bid_id: int
    issuing_org: str | None
    deadline: datetime | None
    project_summary: str | None
    project_scope: str | None
    eval_criteria: list | None
    requirements: list | None
    qualification: str | None
    tech_requirements: list | None
    poison_clauses: dict | None
    risk_level: str | None
    analysis_status: str
    created_at: datetime


class AnalysisStatusResponse(BaseModel):
    bid_id: int
    analysis_status: str
    risk_level: str | None = None


class OutlineResponse(BaseModel):
    id: int
    analysis_id: int
    outline_data: dict
    is_ismp: bool
    created_at: datetime
    updated_at: datetime
