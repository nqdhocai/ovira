import asyncio
import json
from datetime import datetime

from pydantic import BaseModel

from clients import Clients
from configs import get_logger
from hooks.error import FailedExternalAPI, GenericServiceError
from utils.timestamp import floor_to_hour

defillama = Clients.get_service_client().get_defillama_client()
logger = get_logger("dexs")


class ProtocolDexsOverview(BaseModel):
    defillamaId: str
    timestamp: int
    total24hVolume: float | None
    total7dVolume: float | None
    total30dVolume: float | None
    totalAllTimeVolume: float | None


class ChainVolume(BaseModel):
    timestamp: int
    total24h: float | None


async def get_dexs_overview(
    protocolsID: list[str],
) -> list[ProtocolDexsOverview] | None:
    url = "https://api.llama.fi/overview/dexs"
    params = {
        "chain": "solana",
        "excludeTotalDataChart": "true",
        "excludeTotalDataChartBreakdown": "true",
    }
    dexs_overview: list[ProtocolDexsOverview] = []
    try:
        list_protocols = []
        response = await defillama.async_get_request(url=url, params=params)
        for protocol in response["protocols"]:
            if protocol["defillamaId"] in protocolsID:
                list_protocols.append(protocol)
        ts = datetime.utcnow()
        for protocol in response["protocols"]:
            if protocol["defillamaId"] in protocolsID:
                dexs_overview.append(
                    ProtocolDexsOverview(
                        defillamaId=protocol["defillamaId"],
                        timestamp=floor_to_hour(int(ts.timestamp())),
                        total24hVolume=protocol["total24h"]
                        if "total24h" in protocol
                        else None,
                        total7dVolume=protocol["total7d"]
                        if "total7d" in protocol
                        else None,
                        total30dVolume=protocol["total30d"]
                        if "total30d" in protocol
                        else None,
                        totalAllTimeVolume=protocol["totalAllTime"]
                        if "totalAllTime" in protocol
                        else None,
                    )
                )
        return dexs_overview
    except (GenericServiceError, FailedExternalAPI) as e:
        logger.error(f"Error fetching data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


async def get_chain_volume_24h() -> ChainVolume | None:
    url = "https://api.llama.fi/overview/dexs"
    params = {
        "chain": "solana",
        "excludeTotalDataChart": "true",
        "excludeTotalDataChartBreakdown": "true",
    }
    try:
        response = await defillama.async_get_request(url=url, params=params)
        ts = datetime.utcnow()
        return ChainVolume(
            timestamp=floor_to_hour(int(ts.timestamp())),
            total24h=response["total24h"] if "total24h" in response else None,
        )
    except (GenericServiceError, FailedExternalAPI) as e:
        logger.error(f"Error fetching data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(get_dexs_overview())
