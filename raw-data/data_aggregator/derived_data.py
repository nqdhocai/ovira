from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Iterable

from beanie import PydanticObjectId

from mongo.schemas import (
    ChainVolume,
    DeFiLlamaData,
    DerivedData,
    DexsOverview,
    ProtocolsFee,
    ProtocolsMetadata,
    ProtocolsTVL,
)

SECONDS_PER_DAY = 86400


# -------------------- helpers --------------------
def _to_series(series: list[tuple[int, float]] | None) -> list[tuple[int, float]]:
    if not series:
        return []
    out: list[tuple[int, float]] = []
    for it in series:
        try:
            ts, v = int(it[0]), float(it[1])
            if math.isfinite(v):
                out.append((ts, v))
        except Exception:
            continue
    out.sort(key=lambda x: x[0])
    return out


def _nearest_value_at(
    series: list[tuple[int, float]], target_ts: int, tolerance_s: int = 4 * 3600
) -> float | None:
    if not series:
        return None
    # binary-like search
    lo, hi = 0, len(series) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if series[mid][0] < target_ts:
            lo = mid + 1
        else:
            hi = mid - 1
    candidates = []
    if 0 <= lo < len(series):
        candidates.append(series[lo])
    if 0 <= lo - 1 < len(series):
        candidates.append(series[lo - 1])
    if not candidates:
        return None
    ts_best, v_best = min(candidates, key=lambda x: abs(x[0] - target_ts))
    return v_best if abs(ts_best - target_ts) <= tolerance_s else None


def _pct_change_24h_from_series(
    series: list[tuple[int, float]], ts_now: int
) -> float | None:
    if not series:
        return None
    now_val = series[-1][1]
    prev = _nearest_value_at(series, ts_now - SECONDS_PER_DAY)
    if prev is None or prev == 0:
        # fallback: dùng 2 điểm cuối cùng
        if len(series) < 2 or series[-2][1] == 0:
            return None
        prev = series[-2][1]
    return (now_val - prev) / prev


def _slope_per_day(series: list[tuple[int, float]]) -> float | None:
    if len(series) < 2:
        return None
    t0 = series[0][0]
    xs = [(ts - t0) / SECONDS_PER_DAY for ts, _ in series]
    ys = [v for _, v in series]
    n = len(xs)
    mx, my = mean(xs), mean(ys)
    varx = sum((x - mx) ** 2 for x in xs)
    if varx <= 0:
        return 0.0
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    return cov / varx  # USD/ngày


def _cv(series: list[tuple[int, float]]) -> float | None:
    if len(series) < 2:
        return None
    ys = [v for _, v in series]
    mu = mean(ys)
    if mu == 0:
        return None
    return pstdev(ys) / abs(mu)


def _rank_percentile(value: float | None, peers: list[float]) -> float | None:
    vals = [float(v) for v in peers if v is not None and math.isfinite(float(v))]
    if value is None or not math.isfinite(float(value)) or not vals:
        return None
    vals.sort()
    import bisect

    r = bisect.bisect_right(vals, float(value))
    return max(0.0, min(1.0, r / len(vals)))


async def _series_between(
    model, query, start_ts: int, end_ts: int, field_name: str
) -> list[tuple[int, float]]:
    cursor = (
        model.find(query)
        .find(model.timestamp >= start_ts)
        .find(model.timestamp <= end_ts)
        .sort(model.timestamp)  # asc
    )
    docs = await cursor.to_list(None)
    out: list[tuple[int, float]] = []
    for d in docs:
        val = getattr(d, field_name, None)
        if val is not None:
            out.append((int(d.timestamp), float(val)))
    return out


async def _latest_before_or_equal(model, query, as_of: int):
    q = model.find(query).find(model.timestamp <= as_of)
    return await q.sort(-model.timestamp).first_or_none()


async def _latest_per_protocol_in_window(
    as_of: int, hours: int = 6
) -> list[DexsOverview]:
    """Lấy bản ghi DexsOverview mới nhất cho mỗi defillamaId trong cửa sổ [as_of-hours, as_of]."""
    start = as_of - hours * 3600
    docs = await (
        DexsOverview.find(DexsOverview.timestamp >= start)
        .find(DexsOverview.timestamp <= as_of)
        .sort(-DexsOverview.timestamp)
        .to_list(None)
    )
    seen: set[str] = set()
    latest: list[DexsOverview] = []
    for d in docs:
        if d.defillamaId not in seen:
            latest.append(d)
            seen.add(d.defillamaId)
    return latest


def _capacity_usd(
    tvl_usd: float | None,
    chain_vol_24h: float | None,
    prot_vol_24h: float | None,
    alpha: float = 0.05,
    beta: float = 0.03,
    gamma: float = 0.02,
) -> int | None:
    comps: list[float] = []
    if tvl_usd and tvl_usd > 0:
        comps.append(tvl_usd * alpha)
    if chain_vol_24h and chain_vol_24h > 0:
        comps.append(chain_vol_24h * beta)
    if prot_vol_24h and prot_vol_24h > 0:
        comps.append(prot_vol_24h * gamma)
    if not comps:
        return None
    return int(min(comps))


# -------------------- main function --------------------
async def compute_derived_data(
    ts_now: int,
    protocol_id: str,  # defillamaId (vd 'raydium')
    defillama_data: DeFiLlamaData,
) -> DerivedData:
    # 0) Lấy meta để xác định category (để set is_stable_or_lst)
    meta = await ProtocolsMetadata.find_one(
        ProtocolsMetadata.defillamaId == protocol_id
    )
    category = (meta.category if meta else "") or ""
    cat_norm = category.lower()
    is_stable_or_lst = (
        ("liquid staking" in cat_norm)
        or ("liquid restaking" in cat_norm)
        or ("stablecoin" in cat_norm)  # ví dụ: "Partially Algorithmic Stablecoin"
        or ("algorithmic stablecoin" in cat_norm)
    )

    # 1) TVL history 30d (fallback nếu thiếu: build từ ProtocolsTVL.tvl_usd)
    tvl_hist = _to_series(defillama_data.tvl_history_30d)
    if not tvl_hist:
        tvl_hist = await _series_between(
            ProtocolsTVL,
            ProtocolsTVL.protocol.id == (meta.id if meta else PydanticObjectId()),
            ts_now - 30 * SECONDS_PER_DAY,
            ts_now,
            "tvl_usd",
        )

    # 2) dTVL_24h
    dTVL_24h = _pct_change_24h_from_series(tvl_hist, ts_now) if tvl_hist else None

    # 3) slope_tvl_30d & sigma_tvl_30d (CV)
    slope_tvl_30d = _slope_per_day(tvl_hist) if tvl_hist else None
    sigma_tvl_30d = _cv(tvl_hist) if tvl_hist else None

    # 4) fees_history_7d (fallback nếu thiếu: build từ ProtocolsFee.total24h)
    fees_hist = _to_series(defillama_data.fees_history_7d)
    if not fees_hist:
        fees_hist = await _series_between(
            ProtocolsFee,
            ProtocolsFee.defillamaId == protocol_id,
            ts_now - 7 * SECONDS_PER_DAY,
            ts_now,
            "total24h",
        )
    slope_fees_7d = _slope_per_day(fees_hist) if fees_hist else None

    # 5) vol_tvl_ratio_24h
    vol_tvl_ratio_24h = None
    try:
        if defillama_data.dex_volume_24h is not None and defillama_data.tvl_usd not in (
            None,
            0,
        ):
            vol_tvl_ratio_24h = float(defillama_data.dex_volume_24h) / float(
                defillama_data.tvl_usd
            )
    except Exception:
        vol_tvl_ratio_24h = None

    # 6) rank percentiles (lấy peers trong cửa sổ ~6h để chống lệch giờ)
    peer_docs = await _latest_per_protocol_in_window(ts_now, hours=6)
    peers_24h = [d.total24hVolume for d in peer_docs if d.total24hVolume is not None]
    peers_30d = [d.total30dVolume for d in peer_docs if d.total30dVolume is not None]
    volume_24h_rank_pct = (
        _rank_percentile(defillama_data.dex_volume_24h, peers_24h)
        if peers_24h
        else None
    )
    volume_30d_rank_pct = (
        _rank_percentile(defillama_data.dex_volume_30d, peers_30d)
        if peers_30d
        else None
    )

    # 7) offpeg_inst
    # Hiện bạn chưa lưu mapping token-address/giá → không thể tính asset-specific off-peg.
    # Với các protocol không phải stable/LST: đặt 0.0 cho tiện.
    # Với stable/LST: tạm để None (cần thêm dữ liệu, xem gợi ý phía dưới).
    offpeg_inst = 0.0 if not is_stable_or_lst else None

    # 8) capacity_usd
    # stablecoins_chain hiện là list[tuple[str,float]] -> chuyển thành dict để lấy giá trị nếu cần.
    sc_dict: Dict[str, float] = dict(defillama_data.stablecoins_chain or [])
    capacity_usd = _capacity_usd(
        tvl_usd=defillama_data.tvl_usd,
        chain_vol_24h=defillama_data.chain_volume_24h_usd,
        prot_vol_24h=defillama_data.dex_volume_24h,
        alpha=0.05,
        beta=0.03,
        gamma=0.02,
    )

    return DerivedData(
        dTVL_24h=dTVL_24h,
        slope_tvl_30d=slope_tvl_30d,
        sigma_tvl_30d=sigma_tvl_30d,
        slope_fees_7d=slope_fees_7d,
        vol_tvl_ratio_24h=vol_tvl_ratio_24h,
        volume_24h_rank_pct=volume_24h_rank_pct,
        volume_30d_rank_pct=volume_30d_rank_pct,
        offpeg_inst=offpeg_inst,
        is_stable_or_lst=is_stable_or_lst,
        capacity_usd=capacity_usd,
    )
