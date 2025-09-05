from __future__ import annotations

from typing import Any

import numpy as np
from config import FilterConfig
from database.models import Category, ProtocolDoc

# ====================================
# 1) Utilities: normalize & ranking
# ====================================


def minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = np.nanmin(x), np.nanmax(x)
    denom = max(hi - lo, 1e-9)
    return np.clip((x - lo) / denom, 0.0, 1.0)


def pct_rank(x: np.ndarray) -> np.ndarray:
    # percentile rank 1..N / N
    order = x.argsort(kind="mergesort").argsort(kind="mergesort")
    return (order + 1) / (len(x) + 0.0)


def z_to_01(x: np.ndarray) -> np.ndarray:
    mu, sd = np.nanmean(x), np.nanstd(x) + 1e-9
    z = (x - mu) / sd
    # squash về [0,1]
    return np.clip(0.5 + 0.5 * np.tanh(z / 3.0), 0.0, 1.0)


# ====================================
# 2) Config (thresholds & weights)
# ====================================


# ====================================
# 3) Scoring per category
# ====================================


def compute_scores_for_category(
    docs: list[ProtocolDoc], cfg: FilterConfig
) -> list[dict[str, Any]]:
    """
    Returns a list of results: each result includes protocol, category, guardrails_pass, yield/liq/risk/score, reasons.
    Min-max / percentile are computed ON THE BATCH of docs for this category.
    """
    if not docs:
        return []

    # Chuẩn bị vector hóa
    tvl_now = np.array([d.defillama.tvl_usd for d in docs], dtype=float)
    vol24 = np.array([d.defillama.dex_volume_24h_usd or 0.0 for d in docs], dtype=float)
    vol30 = np.array([d.defillama.dex_volume_30d_usd or 0.0 for d in docs], dtype=float)
    cap = np.array([d.derived.capacity_usd or 0.0 for d in docs], dtype=float)

    dTVL_24h = np.array([d.derived.dTVL_24h for d in docs], dtype=float)
    sigma_tvl = np.array([d.derived.sigma_tvl_30d for d in docs], dtype=float)
    slope_tvl = np.array([d.derived.slope_tvl_30d for d in docs], dtype=float)
    slope_fees_7d = np.array(
        [d.derived.slope_fees_7d or 0.0 for d in docs], dtype=float
    )
    vol_tvl_ratio = np.array(
        [d.derived.vol_tvl_ratio_24h or 0.0 for d in docs], dtype=float
    )
    vol24_rank_pct = np.array(
        [
            d.derived.volume_24h_rank_pct
            if d.derived.volume_24h_rank_pct is not None
            else 0.0
            for d in docs
        ],
        float,
    )
    vol30_rank_pct = np.array(
        [
            d.derived.volume_30d_rank_pct
            if d.derived.volume_30d_rank_pct is not None
            else 0.0
            for d in docs
        ],
        float,
    )
    offpeg_inst = np.array([d.derived.offpeg_inst or 0.0 for d in docs], dtype=float)
    is_stable_or_lst = np.array(
        [1.0 if d.derived.is_stable_or_lst else 0.0 for d in docs], dtype=float
    )
    offpeg_sys = np.array([d.off_peg_pct_system() for d in docs], dtype=float)
    apr_fee = np.array([d.apr_fee_annualized() for d in docs], dtype=float)

    qc_days = np.array([d.qc.data_window_days for d in docs], dtype=float)
    qc_missing = np.array([d.qc.missing_points_count for d in docs], dtype=float)

    # ============ Guardrails mask ============
    mask = (
        (qc_days >= cfg.min_window_days)
        & (qc_missing <= cfg.max_missing_points)
        & (dTVL_24h > cfg.min_dTVL_24h)
        & (sigma_tvl <= cfg.max_sigma_tvl_30d)
        & (vol24_rank_pct >= cfg.min_vol24_rank_pct)
        & (vol_tvl_ratio >= cfg.min_vol_tvl_ratio_24h)
        & (cap >= cfg.min_capacity_usd)
        & (
            (is_stable_or_lst == 0.0)
            | (
                (offpeg_inst < cfg.max_offpeg_inst)
                & (offpeg_sys < cfg.max_offpeg_system)
            )
        )
    )

    # For DEX only: apply minimum APR fee threshold
    if docs[0].category == Category.DEX:
        mask = mask & (apr_fee >= cfg.min_apr_fee_for_dex)

    # ============ Yield score ============
    if docs[0].category == Category.DEX:
        y1 = minmax(apr_fee)
        y2 = minmax(vol_tvl_ratio)
        yield_score = 0.6 * y1 + 0.4 * y2

    elif docs[0].category == Category.Lending:
        yield_score = 0.5 * minmax(slope_fees_7d) + 0.5 * minmax(slope_tvl)

    elif docs[0].category == Category.LST:
        yield_score = minmax(slope_tvl)

    elif docs[0].category == Category.Vault:
        sustain = slope_tvl - sigma_tvl
        yield_score = minmax(sustain)

    elif docs[0].category == Category.Deriv:
        # If there is no 7d perps volume series yet → temporarily use vol30 rank as a proxy
        yield_score = vol30_rank_pct.copy()

    else:
        yield_score = np.zeros(len(docs), dtype=float)

    # ============ Liquidity score ============
    liq_score = (
        cfg.lam_vol24 * pct_rank(vol24)
        + cfg.lam_vol30 * pct_rank(vol30)
        + cfg.lam_capacity * pct_rank(cap)
    )

    # ============ Risk score ============
    r_tvl = z_to_01(-dTVL_24h)
    r_instab = minmax(sigma_tvl)
    # already have rank_pct for 30d volume ⇒ r_liq is low when volume is high
    r_liq = 1.0 - np.clip(vol30_rank_pct, 0.0, 1.0)
    r_off = np.where(is_stable_or_lst > 0.5, minmax(offpeg_inst), 0.0)

    risk_score = (
        cfg.w_tvl_drop * r_tvl
        + cfg.w_liq * r_liq
        + cfg.w_instab * r_instab
        + cfg.w_offpeg * r_off
    )

    # ============ Composite ============
    score = cfg.wy * yield_score + cfg.wl * liq_score - cfg.wr * risk_score
    score = np.where(mask, score, -1.0)

    results: list[dict[str, Any]] = []
    for i, d in enumerate(docs):
        guardrails_passed = []
        if mask[i]:
            guardrails_passed = [
                "window>=30d",
                "missing<=2",
                "no-panic-drop",
                "sigma<=max",
                "vol_rank24>=50%",
                "vol/tvl>=0.10",
                "capacity>=50k",
            ]
            if d.category == Category.DEX:
                guardrails_passed.append("APR_fee>=5%")
            if d.derived.is_stable_or_lst:
                guardrails_passed.append("offpeg<2% (inst & system)")

        results.append({
            "protocol": d.protocol,
            "category": d.category.value,
            "score": round(float(score[i]), 4),
            "yield": round(float(yield_score[i]), 4),
            "liquidity": round(float(liq_score[i]), 4),
            "risk": round(float(risk_score[i]), 4),
            "guardrails_ok": bool(mask[i]),
            "guardrails_passed": guardrails_passed,
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def rank_all(
    docs: list[ProtocolDoc],
    cfg: FilterConfig = FilterConfig(),
    quotas: dict[Category, int] | None = None,
    top_k_total: int = 6,
) -> dict[str, Any]:
    cfg = cfg or FilterConfig()
    # group by category
    by_cat: dict[Category, list[ProtocolDoc]] = {}
    for d in docs:
        by_cat.setdefault(d.category, []).append(d)

    results_by_cat: dict[Category, list[dict[str, Any]]] = {}
    for cat, lst in by_cat.items():
        results_by_cat[cat] = compute_scores_for_category(lst, cfg)

    # Select by quota (default)
    if quotas is None:
        quotas = {
            Category.DEX: 2,
            Category.Lending: 2,
            Category.LST: 1,
            Category.Vault: 1,
            Category.Deriv: 0,
        }

    picked: list[dict[str, Any]] = []
    for cat in [
        Category.DEX,
        Category.Lending,
        Category.LST,
        Category.Vault,
        Category.Deriv,
    ]:
        want = quotas.get(cat, 0)
        cand = [
            r
            for r in results_by_cat.get(cat, [])
            if r["guardrails_ok"] and r["score"] >= 0.0
        ]
        picked.extend(cand[:want])

    # If not enough top_k_total, take additional best-remaining
    if len(picked) < top_k_total:
        rest: list[dict[str, Any]] = []
        for cat, arr in results_by_cat.items():
            for r in arr:
                if r not in picked and r["guardrails_ok"] and r["score"] >= 0.0:
                    rest.append(r)
        rest.sort(key=lambda r: r["score"], reverse=True)
        need = top_k_total - len(picked)
        picked.extend(rest[:need])

    picked.sort(key=lambda r: r["score"], reverse=True)
    return {"picked": picked, "by_category": results_by_cat}
