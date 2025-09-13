from datetime import datetime
from typing import Annotated
from uuid import UUID

import pymongo
from beanie import Document, Indexed, Link
from pydantic import BaseModel, Field


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
    pool_charts_30d: list[PoolCharts] | None

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


DocumentModels = [PoolsSnapshot, PoolsMetdadata]
