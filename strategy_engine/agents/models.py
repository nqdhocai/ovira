from enum import Enum
from typing import Literal

from pydantic import BaseModel
from utils.models import RiskLabel


class AllocationItem(BaseModel):
    pool_name: str
    weight_pct: float


class AgentMessage(BaseModel):
    role: Literal["planner", "critic", "verifier"]
    content: str


class Strategy(BaseModel):
    risk_label: RiskLabel
    allocations: list[AllocationItem]


class FinalStrategy(BaseModel):
    strategy: Strategy
    reasoning_trace: list[AgentMessage] | None


class SupportedTokens(Enum):
    USDT = "USDT"
    USDC = "USDC"


class TraceItem(BaseModel):
    role: Literal["planner", "verifier", "critic", "orchestrator", "system", "tool"]
    content: str
    raw: str
    status: str | None
    thread_id: str | None
    message_id: str | None
    timestamp_ms: str | None
    tool_name: str | None
    tool_input: str | None
    tool_output: str | None


class Allocation(BaseModel):
    pool_name: str
    weight_pct: float


class Totals(BaseModel):
    weight_pct_sum: float


class PlannerOutput(BaseModel):
    rationale: str
    allocations: list[Allocation]
    totals: Totals
