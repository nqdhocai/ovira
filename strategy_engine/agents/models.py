from pydantic import BaseModel
from utils.models import RiskLabel


class AllocationItem(BaseModel):
    pool_id: str
    weight_pct: float


class Strategy(BaseModel):
    risk_label: RiskLabel
    allocations: list[AllocationItem]


class FinalStrategyResponse(BaseModel):
    strategy: Strategy
    reasons: list[str]
    critic_notes: list[str]
