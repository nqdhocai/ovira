from pydantic import BaseModel

# ====================================
# 2) Config (thresholds & weights)
# ====================================


class FilterConfig(BaseModel):
    # guardrails
    min_window_days: int = 30
    max_missing_points: int = 2
    min_dTVL_24h: float = -0.30
    max_sigma_tvl_30d: float = 0.35
    min_vol24_rank_pct: float = 0.50
    min_vol_tvl_ratio_24h: float = 0.10
    min_capacity_usd: float = 50_000.0
    max_offpeg_inst: float = 0.02
    max_offpeg_system: float = 0.02
    min_apr_fee_for_dex: float = 0.05

    # weights
    # composite
    wy: float = 0.45
    wl: float = 0.25
    wr: float = 0.30
    # risk parts
    w_tvl_drop: float = 0.35
    w_liq: float = 0.25
    w_instab: float = 0.25
    w_offpeg: float = 0.15
    # liquidity parts
    lam_vol24: float = 0.5
    lam_vol30: float = 0.2
    lam_capacity: float = 0.3
