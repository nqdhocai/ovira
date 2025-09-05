import asyncio
import json

from pydantic import BaseModel

from clients import Clients
from configs import get_logger
from hooks.error import FailedExternalAPI, GenericServiceError

defillama = Clients.get_service_client().get_defillama_client()
logger = get_logger("protocols")


class Protocol(BaseModel):
    defillamaId: str
    name: str
    symbol: str
    url: str
    description: str
    category: str
    slug: str


async def get_protocols_metadata() -> list[Protocol] | None:
    """Fetch data from the meta protocols endpoint by DeFiLlama."""
    url = "https://api.llama.fi/protocols"
    finance_categories = [
        "Liquid Staking",
        "Lending",
        "Liquid Restaking",
        "Yield Aggregator",
        "Liquidity manager",
        "Dexs",
        "CDP",
        "Staking Pool",
        "Options",
        "Derivatives",
        "RWA Lending",
        "Synthetics",
        "Farm",
    ]
    try:
        response = await defillama.async_get_request(url)
        finance_protocols: list[Protocol] = []
        for protocol in response:
            for chain in protocol["chains"]:
                if chain == "Solana" and protocol["category"] in finance_categories:
                    finance_protocols.append(
                        Protocol(
                            defillamaId=protocol["id"],
                            name=protocol["name"],
                            symbol=protocol["symbol"],
                            url=protocol["url"],
                            description=protocol["description"],
                            category=protocol["category"],
                            slug=protocol["slug"],
                        )
                    )
        logger.info(f"Total finance protocols on Solana: {len(finance_protocols)}")
        return finance_protocols
    except (GenericServiceError, FailedExternalAPI) as e:
        logger.error(f"Error fetching data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(get_protocols_metadata())
