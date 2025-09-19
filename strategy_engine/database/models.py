import bisect
from datetime import datetime, timedelta, timezone
from uuid import UUID

from beanie import Document
from pydantic import BaseModel, Field, model_validator


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


class Predictions(BaseModel):
    predictedClass: str | None = None
    predictedProbability: float | None = None
    binnedConfidence: int | None = None


class ApyStatistics(BaseModel):
    mu: float
    sigma: float
    count: int


class Chart(BaseModel):
    timestamp: datetime
    tvlUsd: float
    apy: float


class PoolSnapshotMinimal(BaseModel):
    pool_name: str
    apy_statistics: ApyStatistics
    apyPct1D: float | None = None
    apyPct7D: float | None = None
    apyPct30D: float | None = None
    tvlUsd: float | None = None


class PoolSnapshot(Document):
    id: UUID = Field(alias="_id")
    # chain: str
    # project: str
    symbol: str
    pool_name: str
    predictions: Predictions
    apy_statistics: ApyStatistics
    update_at: datetime
    pool_charts_30d: list[Chart] | None

    apyPct1D: float | None = None
    apyPct7D: float | None = None
    apyPct30D: float | None = None
    tvlUsd: float | None = None

    @model_validator(mode="after")
    def compute_from_charts(
        self,
        now: datetime | None = None,
        max_gap_hours: float = 12.0,
        stats_window_days: int | None = None,  # None = all data
        use_linear_interpolation: bool = False,
    ) -> "PoolData":
        """
        - Calculate apyPct1D/7D/30D based on time points, robust to uneven sampling.
        - Update tvlUsd at the latest point.
        """
        if not self.pool_charts_30d:
            return self

        charts_sorted = sorted(self.pool_charts_30d, key=lambda c: c.timestamp)
        times = [
            c.timestamp
            if c.timestamp.tzinfo
            else c.timestamp.replace(tzinfo=timezone.utc)
            for c in charts_sorted
        ]
        apys = [c.apy for c in charts_sorted]
        tvls = [c.tvlUsd for c in charts_sorted]

        if now is None:
            now = times[-1]
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        self.tvlUsd = tvls[-1]

        # 2) Internal function: get value at target time (interpolate or nearest-left)
        max_gap = timedelta(hours=max_gap_hours)

        def value_at(target: datetime, series: list[float]) -> float | None:
            """
            Return value at 'target' timestamp by:
            - Linear interpolation if bracketed by 2 points and distance doesn't exceed max_gap;
            - Otherwise, use 'nearest left' value if distance <= max_gap;
            - Otherwise, None.
            """
            idx = bisect.bisect_left(times, target)

            # Case: exact timestamp match
            if idx < len(times) and times[idx] == target:
                return series[idx]

            left_i = idx - 1
            right_i = idx

            left_ok = left_i >= 0
            right_ok = right_i < len(times)

            # Both sides bracket the target -> try interpolation
            if use_linear_interpolation and left_ok and right_ok:
                t0, t1 = times[left_i], times[right_i]
                v0, v1 = series[left_i], series[right_i]
                # Check gap on both sides
                if (target - t0) <= max_gap and (t1 - target) <= max_gap:
                    # linear interpolation in time
                    span = (t1 - t0).total_seconds()
                    if span > 0:
                        alpha = (target - t0).total_seconds() / span
                        return v0 + alpha * (v1 - v0)

            # if cant interpolate, try nearest left
            if left_ok and (target - times[left_i]) <= max_gap:
                return series[left_i]

            # Or right nearest (rarely used for past pct, but for completeness)
            if right_ok and (times[right_i] - target) <= max_gap:
                return series[right_i]

            return None

        def pct_change(old: float | None, new: float | None) -> float | None:
            if old is None or new is None or old == 0:
                return None
            return (new - old) / old * 100.0

        # 3) Calculate percentage change based on time points
        latest_apy = apys[-1]
        apy_1d_ago = value_at(now - timedelta(days=1), apys)
        apy_7d_ago = value_at(now - timedelta(days=7), apys)
        apy_30d_ago = value_at(now - timedelta(days=30), apys)

        self.apyPct1D = pct_change(apy_1d_ago, latest_apy)
        self.apyPct7D = pct_change(apy_7d_ago, latest_apy)
        self.apyPct30D = pct_change(apy_30d_ago, latest_apy)

        self.pool_charts_30d = None  # free memory

        return self

    class Settings:
        name: str = "pools_snapshot_v1"
