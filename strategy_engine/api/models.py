from enum import Enum
from typing import Any

from pydantic import BaseModel
from utils.models import RiskLabel


class GlobalStrategyRequest(BaseModel):
    risk_label: RiskLabel
    policy: str | dict[str, Any] | None = None


class SupportedTokens(str, Enum):
    USDC = "USDC"
    USDT = "USDT"
