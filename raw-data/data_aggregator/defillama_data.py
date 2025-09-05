from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from beanie import PydanticObjectId

from mongo.schemas import (
    ChainVolume,
    DeFiLlamaData,
    DexsOverview,
    ProtocolsFee,
    ProtocolsMetadata,
    ProtocolsTVL,
    StableCoinsData,
)

SECONDS_PER_DAY = 86400


async def _get_protocol_meta_by_defillama(
    defillama_id: str,
) -> ProtocolsMetadata | None:
    return await ProtocolsMetadata.find_one(
        ProtocolsMetadata.defillamaId == defillama_id
    )


async def _latest_before_or_equal(model, query, as_of: int | None):
    q = model.find(query)
    if as_of is not None:
        q = q.find(model.timestamp <= as_of)
    return await q.sort(-model.timestamp).first_or_none()


async def _series_between(
    model, query, start_ts: int, end_ts: int, field_name: str
) -> list[tuple[int, float]]:
    # trả về list[(timestamp, value)] cho field chỉ định, bỏ None
    cursor = (
        model.find(query)
        .find(model.timestamp >= start_ts)
        .find(model.timestamp <= end_ts)
        .sort(model.timestamp)  # ascending
    )
    docs = await cursor.to_list(None)
    out: list[tuple[int, float]] = []
    for d in docs:
        val = getattr(d, field_name, None)
        if val is not None:
            out.append((int(d.timestamp), float(val)))
    return out


async def aggregate_defillama_data(
    protocol_id: str,
    timestamp: int,  # unix ts (floored to hour); mặc định = giờ hiện tại
) -> DeFiLlamaData:
    """
    Tổng hợp dữ liệu từ Mongo (đã crawl từ DefiLlama) thành DeFiLlamaData cho 1 protocol.
    - protocol_id: id của protocol trên DefiLlama (vd: 'raydium', 'orca', 'solend'...)
    - timestamp: thời điểm chốt (<=), mặc định 'now' (floored to hour)
    """
    as_of = timestamp
    start_7d = timestamp - 7 * 86400
    start_30d = timestamp - 30 * 86400

    # ---- Resolve protocol metadata (để join sang ProtocolsTVL) ----
    meta = await _get_protocol_meta_by_defillama(protocol_id)
    if not meta:
        # Không tìm thấy protocol => trả về rỗng
        return DeFiLlamaData(
            tvl_usd=None,
            tvl_history_30d=None,
            dex_volume_24h=None,
            dex_volume_30d=None,
            dex_volume_history_30d=None,
            fees_24h_usd=None,
            fees_history_7d=None,
            stablecoins_chain=None,
            chain_volume_24h_usd=None,
        )

    # ---- TVL (current + history 30d) ----
    tvl_row = await _latest_before_or_equal(
        ProtocolsTVL,
        ProtocolsTVL.protocol.id == meta.id,
        as_of,
    )
    tvl_usd = tvl_row.tvl_usd if tvl_row else None
    # Ưu tiên dùng trường đã có 'tvl_history_30d' trong 1 bản ghi mới nhất
    tvl_history_30d = (
        tvl_row.tvl_history_30d if (tvl_row and tvl_row.tvl_history_30d) else None
    )

    # ---- DEX volumes (24h, 30d, history 30d từ snapshot 24h theo từng giờ) ----
    dexs_latest = await _latest_before_or_equal(
        DexsOverview,
        DexsOverview.defillamaId == protocol_id,
        as_of,
    )
    dex_volume_24h = dexs_latest.total24hVolume if dexs_latest else None
    dex_volume_30d = dexs_latest.total30dVolume if dexs_latest else None

    dex_volume_history_30d = await _series_between(
        DexsOverview,
        DexsOverview.defillamaId == protocol_id,
        start_30d,
        as_of,
        "total24hVolume",
    )
    dex_volume_history_30d = dex_volume_history_30d or None  # rỗng => None

    # ---- Fees (24h + history 7d từ snapshot 24h) ----
    fee_latest = await _latest_before_or_equal(
        ProtocolsFee,
        ProtocolsFee.defillamaId == protocol_id,
        as_of,
    )
    fees_24h_usd = fee_latest.total24h if fee_latest else None

    fees_history_7d = await _series_between(
        ProtocolsFee,
        ProtocolsFee.defillamaId == protocol_id,
        start_7d,
        as_of,
        "total24h",
    )
    fees_history_7d = fees_history_7d or None

    # ---- Stablecoins (chain-level) ----
    st_latest = await _latest_before_or_equal(StableCoinsData, {}, as_of)
    stablecoins_chain: list[tuple[str, float]] = []
    if st_latest:
        # Bạn hiện đang lưu tổng chain, không có breakdown theo USDC.
        # Đưa thẳng vào dict theo schema hiện tại.
        stablecoins_chain.append(
            ("usdc_mcap", st_latest.totalCirculatingUSD or None),
        )
        stablecoins_chain.append(
            ("off_peg_pct", st_latest.off_peg_pct or None),
        )

    # ---- Chain-wide DEX volume 24h ----
    chain_vol_latest = await _latest_before_or_equal(ChainVolume, {}, as_of)
    chain_volume_24h_usd = chain_vol_latest.volume_24h_usd if chain_vol_latest else None

    return DeFiLlamaData(
        tvl_usd=tvl_usd,
        tvl_history_30d=tvl_history_30d,
        dex_volume_24h=dex_volume_24h,
        dex_volume_30d=dex_volume_30d,
        dex_volume_history_30d=dex_volume_history_30d,
        fees_24h_usd=fees_24h_usd,
        fees_history_7d=fees_history_7d,
        stablecoins_chain=stablecoins_chain,
        chain_volume_24h_usd=chain_volume_24h_usd,
    )
