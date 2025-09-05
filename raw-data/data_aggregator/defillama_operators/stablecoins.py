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
logger = get_logger("stablecoins")


class Stablecoin(BaseModel):
    timestamp: int
    totalCirculating: float | None
    totalCirculatingUSD: float | None
    off_peg_pct: float | None


async def get_stablecoins_data() -> Stablecoin | None:
    url = f"https://stablecoins.llama.fi/stablecoincharts/Solana"
    try:
        response = await defillama.async_get_request(url=url)
        last_day_data = response[-1]
        peg = last_day_data["totalCirculating"]["peggedUSD"]
        mkt = last_day_data["totalCirculatingUSD"]["peggedUSD"]
        ts = datetime.utcnow()
        return Stablecoin(
            timestamp=floor_to_hour(int(ts.timestamp())),
            totalCirculating=peg,
            totalCirculatingUSD=mkt,
            off_peg_pct=abs(mkt - peg) / peg * 100,
        )
    except (GenericServiceError, FailedExternalAPI) as e:
        logger.error(f"get_stablecoins_data error: {e}")
    except Exception as e:
        logger.error(f"get_stablecoins_data unexpected error: {e}")


if __name__ == "__main__":
    result = asyncio.run(get_stablecoins_data())
    if result:
        print(result)
