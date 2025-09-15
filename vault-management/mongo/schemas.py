from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from beanie import Document, Link
from pydantic import BaseModel


class Predictions(BaseModel):
    predictedClass: str | None
    predictedProbability: float | None
    binnedConfidence: float | None


class APYStatistics(BaseModel):
    mu: float | None
    sigma: float | None
    count: int | None


class PoolCharts(BaseModel):
    timestamp: datetime
    tvlUsd: float | None
    apy: float | None


class PoolsSnapshot(Document):
    id: UUID
    chain: str
    update_at: datetime
    project: str
    symbol: str
    pool_name: str
    predictions: Predictions
    apy_statistics: APYStatistics
    pool_charts_30d: list[PoolCharts]

    class Settings:
        name = "pools_snapshot_v1"
        validate_on_save = True


class PoolsMetdadata(Document):
    id: UUID
    defillama_id: str | None
    url: str | None
    project: str
    name: str | None
    symbol: str
    chain: str
    final_name: str

    class Settings:
        name = "pools_metadata"
        validate_on_save = True


class PoolAllocation(BaseModel):
    pool_name: str
    weight_pct: float


class Strategy(BaseModel):
    risk_label: str
    allocations: list[PoolAllocation]


class StrategyInfo(BaseModel):
    strategy: Strategy
    reasons: list[str]
    critic_notes: list[str]


class UpdatedInfo(BaseModel):
    action: str
    details: str


class UserMetadata(Document):
    id: UUID
    wallet_address: str

    class Settings:
        name = "user_metadata"
        validate_on_save = True


class VaultsMetadata(Document):
    id: UUID
    name: str
    address: str | None
    owner: Link[UserMetadata]
    asset: str  # e.g., 'USDT', 'USDC'
    created_at: datetime
    update_frequency: float  # in hours
    policy_prompt: str | None

    class Settings:
        name = "vaults_metadata"
        validate_on_save = True


class VaultsStrategy(Document):
    id: UUID
    update_at: datetime
    vault: Link[VaultsMetadata]
    apy: float
    strategy: StrategyInfo

    class Settings:
        name = "vaults_strategy"
        validate_on_save = True


class VaultsHistory(Document):
    id: UUID
    update_at: datetime
    vault: Link[VaultsMetadata]
    tvl: float

    class Settings:
        name = "vaults_history"
        validate_on_save = True


class VaultsUpdated(Document):
    id: UUID
    update_at: datetime
    vault: Link[VaultsMetadata]
    last_updated: UpdatedInfo

    class Settings:
        name = "vaults_updated"
        validate_on_save = True


class Transaction(Document):
    id: UUID
    timestamp: datetime
    user: Link[UserMetadata]
    vault: Link[VaultsMetadata]
    type: Literal["deposit", "withdrawal"]
    amount: float

    class Settings:
        name = "transactions"
        validate_on_save = True


class UserBalanceHistory(Document):
    id: UUID
    user: Link[UserMetadata]
    vault: Link[VaultsMetadata]
    balance: float
    update_at: datetime

    class Settings:
        name = "user_balances"
        validate_on_save = True


DocumentModels = [
    PoolsSnapshot,
    VaultsStrategy,
    VaultsHistory,
    VaultsUpdated,
    Transaction,
    VaultsMetadata,
    UserMetadata,
    UserBalanceHistory,
    PoolsMetdadata,
]
