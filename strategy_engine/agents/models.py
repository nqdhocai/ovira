from enum import Enum
from typing import Literal

from pydantic import BaseModel
from utils.models import RiskLabel


class AllocationItem(BaseModel):
    pool_name: str
    weight_pct: float


class ConversationSummary(BaseModel):
    role: Literal["planner", "critic", "verifier"]
    content: str


class Strategy(BaseModel):
    risk_label: RiskLabel
    allocations: list[AllocationItem]


class FinalStrategy(BaseModel):
    strategy: Strategy
    reasoning_trace: list[ConversationSummary]


class SupportedTokens(Enum):
    USDT = "USDT"
    USDC = "USDC"
