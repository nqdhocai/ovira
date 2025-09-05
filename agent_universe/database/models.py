from enum import Enum

from beanie import Document
from pydantic import BaseModel


class Category(str, Enum):
    DEX = "DEX"
    Lending = "Lending"
    LST = "LST"
    Vault = "Vault"
    Deriv = "Deriv"


class DefiLlamaData(BaseModel):
    tvl_usd: float
    dex_volume_24h_usd: float | None = 0.0
    dex_volume_30d_usd: float | None = 0.0
    fees_24h_usd: float | None = 0.0
    stablecoins_chain: dict[str, float] | None = (
        None  # {"usdc_mcap":..., "off_peg_pct":...}
    )


class Derived(BaseModel):
    dTVL_24h: float
    slope_tvl_30d: float
    sigma_tvl_30d: float
    slope_fees_7d: float | None = 0.0
    vol_tvl_ratio_24h: float | None = 0.0
    volume_24h_rank_pct: float | None = None
    volume_30d_rank_pct: float | None = None
    offpeg_inst: float | None = 0.0
    is_stable_or_lst: bool = False
    capacity_usd: float | None = 0.0


class QC(BaseModel):
    missing_points_count: int = 0
    data_window_days: int = 30


class ProtocolDoc(Document):
    timestamp: int
    chain: str
    protocol: str
    category: Category
    defillama: DefiLlamaData
    derived: Derived
    qc: QC

    # Tự tính APR phí annualized khi cần (cho DEX)
    def apr_fee_annualized(self) -> float:
        fees = self.defillama.fees_24h_usd or 0.0
        tvl = self.defillama.tvl_usd or 0.0
        if tvl <= 0:
            return 0.0
        return (fees / tvl) * 365.0

    def off_peg_pct_system(self) -> float:
        if (
            self.defillama.stablecoins_chain
            and "off_peg_pct" in self.defillama.stablecoins_chain
        ):
            return float(self.defillama.stablecoins_chain["off_peg_pct"])
        return 0.0
