import asyncio
import json
import time
from datetime import datetime

from pydantic import BaseModel

from clients import Clients
from configs import get_logger
from hooks.error import FailedExternalAPI, GenericServiceError
from utils.timestamp import floor_to_hour

defillama = Clients.get_service_client().get_defillama_client()
logger = get_logger("tvl")


class ProtocolTVL(BaseModel):
    timestamp: int
    tvl_change_24h: float | None
    tvl_change_7d: float | None
    tvl_change_30d: float | None
    tvl_usd: float | None
    tvl_history_30d: list[tuple[int, float]] | None


async def get_protocols_tvl(protocol_slug: str) -> ProtocolTVL | None:
    url = f"https://api.llama.fi/protocol/{protocol_slug}"
    try:
        response = await defillama.async_get_request(url=url)

        current_time = time.time()
        day_ago = current_time - 86400 - 86400
        week_ago = current_time - 604800 - 86400
        month_ago = current_time - 2592000 - 86400
        last_24h_tvl = [
            item["totalLiquidityUSD"]
            for item in response["chainTvls"]["Solana"]["tvl"]
            if item["date"] >= day_ago
        ]
        last_7d_tvl = [
            item["totalLiquidityUSD"]
            for item in response["chainTvls"]["Solana"]["tvl"]
            if item["date"] >= week_ago
        ]
        last_30d_tvl = [
            item["totalLiquidityUSD"]
            for item in response["chainTvls"]["Solana"]["tvl"]
            if item["date"] >= month_ago
        ]
        all_time_tvl = [
            item["totalLiquidityUSD"] for item in response["chainTvls"]["Solana"]["tvl"]
        ]
        tvl_history_30d = [
            (item["date"], item["totalLiquidityUSD"])
            for item in response["chainTvls"]["Solana"]["tvl"]
            if item["date"] >= month_ago
        ]

        ts = datetime.utcnow()

        return ProtocolTVL(
            timestamp=floor_to_hour(int(ts.timestamp())),
            tvl_change_24h=last_24h_tvl[-1] - last_24h_tvl[0],
            tvl_change_7d=last_7d_tvl[-1] - last_7d_tvl[0],
            tvl_change_30d=last_30d_tvl[-1] - last_30d_tvl[0],
            tvl_usd=all_time_tvl[-1],
            tvl_history_30d=tvl_history_30d,
        )

    except (GenericServiceError, FailedExternalAPI) as e:
        logger.error(f"get_protocols_tvl error: {e}")
    except Exception as e:
        logger.error(f"get_protocols_tvl unexpected error: {e}")


if __name__ == "__main__":
    res = asyncio.run(get_protocols_tvl("lido"))
    print(res)
