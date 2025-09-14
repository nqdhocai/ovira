from typing import Any, Literal

from agents.models import FinalStrategyResponse
from pydantic import BaseModel
from utils.models import RiskLabel


class APIResponse(BaseModel):
    status: Literal["success", "error"]
    error: str | None


class GlobalStrategyRequest(BaseModel):
    risk_label: RiskLabel
    policy: str | dict[str, Any] | None = None


class StrategyResponse(APIResponse):
    strategy: FinalStrategyResponse | None = None
