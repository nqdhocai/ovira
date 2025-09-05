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
logger = get_logger("fee")


class ProtocolFee(BaseModel):
    defillamaId: str
    timestamp: int
    total24h: float | None
    total7d: float | None
    total30d: float | None


async def get_protocols_fee(protocol_slug: str, protocol_id: str) -> ProtocolFee | None:
    url = f"https://api.llama.fi/summary/fees/{protocol_slug}"
    try:
        response = await defillama.async_get_request(url=url)
        ts = datetime.utcnow()
        return ProtocolFee(
            defillamaId=response["id"],
            timestamp=floor_to_hour(int(ts.timestamp())),
            total24h=response["total24h"] if "total24h" in response else None,
            total7d=response["total7d"] if "total7d" in response else None,
            total30d=response["total30d"] if "total30d" in response else None,
        )
    except (GenericServiceError, FailedExternalAPI) as e:
        logger.error(f"get_protocols_fee error: {e}")
    except Exception as e:
        logger.error(f"get_protocols_fee unexpected error: {e}")
