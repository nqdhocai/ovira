from datetime import datetime
from typing import Annotated
from uuid import UUID

import pymongo
from beanie import Document, Indexed, Link
from pydantic import BaseModel, Field


class ProtocolsMetadata(Document):
    id: UUID
    defillamaId: str
    url: Annotated[str, Indexed(index_type=pymongo.TEXT)]
    name: str
    symbol: str
    description: str
    category: str
    slug: str

    class Settings:
        name: str = "protocols_metadata"
        validate_on_save: bool = True


class DexsOverview(Document):
    id: UUID
    protocol: Link[ProtocolsMetadata]
    defillamaId: str
    timestamp: int  # Unix timestamp that floors to the hour
    total24hVolume: float | None
    total7dVolume: float | None
    total30dVolume: float | None
    totalAllTimeVolume: float | None

    class Settings:
        name: str = "dexs_overview"
        validate_on_save: bool = True


class ProtocolsTVL(Document):
    id: UUID
    protocol: Link[ProtocolsMetadata]
    timestamp: int  # Unix timestamp that floors to the hour
    tvl_change_24h: float | None
    tvl_change_7d: float | None
    tvl_change_30d: float | None
    tvl_usd: float
    tvl_history_30d: list[tuple[int, float]] | None

    class Settings:
        name: str = "protocols_tvl"
        validate_on_save: bool = True


class ProtocolsFee(Document):
    id: UUID
    protocol: Link[ProtocolsMetadata]
    defillamaId: str
    timestamp: int  # Unix timestamp that floors to the hour
    total24h: float | None
    total7d: float | None
    total30d: float | None

    class Settings:
        name: str = "protocols_fee"
        validate_on_save: bool = True


class StableCoinsData(Document):
    id: UUID
    timestamp: int  # Unix timestamp that floors to the hour
    totalCirculating: float | None
    totalCirculatingUSD: float | None
    off_peg_pct: float | None

    class Settings:
        name: str = "stable_coins_data"
        validate_on_save: bool = True


class ChainVolume(Document):
    id: UUID
    timestamp: int  # Unix timestamp that floors to the hour
    volume_24h_usd: float | None

    class Settings:
        name: str = "chain_volume_history"
        validate_on_save: bool = True


class ProtocolPrimaryAsset(Document):
    id: UUID
    defillamaId: str  # 'marinade', 'jito', ...
    chain: str  # 'solana'
    token_symbol: str  # 'mSOL'
    token_address: str  # mint address trên Solana
    kind: str  # 'lst' | 'stable' | 'other'

    class Settings:
        name = "protocol_primary_asset"
        validate_on_save = True


class TokenPriceSnapshot(Document):
    id: UUID
    timestamp: int  # floored hour
    chain: str  # 'solana'
    token_address: str
    price_usd: float | None

    class Settings:
        name = "token_price_snapshots"
        validate_on_save = True


class DeFiLlamaData(BaseModel):
    tvl_usd: float | None
    tvl_history_30d: list[tuple[int, float]] | None
    dex_volume_24h: float | None
    dex_volume_30d: float | None
    dex_volume_history_30d: list[tuple[int, float]] | None
    fees_24h_usd: float | None
    fees_history_7d: list[tuple[int, float]] | None
    stablecoins_chain: list[tuple[str, float]]
    chain_volume_24h_usd: float | None


class DerivedData(BaseModel):
    dTVL_24h: float | None
    slope_tvl_30d: float | None
    sigma_tvl_30d: float | None
    slope_fees_7d: float | None
    vol_tvl_ratio_24h: float | None
    volume_24h_rank_pct: float | None
    volume_30d_rank_pct: float | None
    offpeg_inst: float | None
    is_stable_or_lst: bool
    capacity_usd: int | None


class ProtocolSnapshot(Document):
    id: UUID
    timestamp: int  # Unix timestamp that floors to the hour
    chain: str
    protocol: str
    category: str
    defillama: DeFiLlamaData
    derived: DerivedData

    class Settings:
        name: str = "protocol_snapshots_v1"
        validate_on_save: bool = True


DocumentModels = [
    ProtocolsMetadata,
    DexsOverview,
    ProtocolsTVL,
    ProtocolsFee,
    StableCoinsData,
    ChainVolume,
    ProtocolPrimaryAsset,
    TokenPriceSnapshot,
    ProtocolSnapshot,
]
