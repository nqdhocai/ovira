import asyncio
import json
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from clients import Clients
from configs import get_logger
from hooks.error import FailedExternalAPI, GenericServiceError
from mongo.schemas import (
    APYStatistics,
    PoolCharts,
    PoolsMetdadata,
    PoolsSnapshot,
    Predictions,
)
from utils import hasher

defillama = Clients.get_service_client().get_defillama_client()
mongo_client = Clients.get_mongo_client()
logger = get_logger("defillama_stable_solana_pools")


def parse_iso_datetime_naive(date_str: str) -> datetime:
    if date_str.endswith("Z"):
        date_str = date_str.replace("Z", "+00:00")
    return datetime.fromisoformat(date_str).replace(tzinfo=None)


async def get_pool_charts_30d(pool_address: str) -> list[PoolCharts]:
    url = f"https://yields.llama.fi/chart/{pool_address}"
    try:
        response = await defillama.async_get_request(url=url)
        charts_data = response["data"]
        # Filter data for the last 30 days
        last_30d = datetime.utcnow() - timedelta(days=30)
        # with open(f"debug_charts_{pool_address}.json", "w") as f:
        #     json.dump(charts_data, f)
        pool_charts_30d: list[PoolCharts] = []
        for item in charts_data:
            # Parse ISO format datetime string
            ts = parse_iso_datetime_naive(item["timestamp"])
            if ts >= last_30d:
                pool_charts_30d.append(
                    PoolCharts(
                        timestamp=ts,
                        tvlUsd=item["tvlUsd"],
                        apy=item["apy"],
                    )
                )
        return pool_charts_30d
    except (GenericServiceError, FailedExternalAPI) as e:
        logger.error(f"Error fetching pool charts for {pool_address}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching pool charts for {pool_address}: {e}")
        return []


async def aggregate_solana_stable_pools():
    url = "https://yields.llama.fi/pools"
    await mongo_client.initialize()
    try:
        response = await defillama.async_get_request(url=url)
        pools = response["data"]
        solana_pools = [pool for pool in pools if pool["chain"] == "Solana"]
        stable_solana_pools = [
            pool
            for pool in solana_pools
            if pool["stablecoin"] == True
            and (pool["symbol"] == "USDT" or pool["symbol"] == "USDC")
        ]
        logger.info(f"Found {len(stable_solana_pools)} stable Solana pools.")
        for pool in stable_solana_pools:
            pool_charts_30d = await get_pool_charts_30d(pool["pool"])
            pool_predictions = Predictions.model_validate(pool["predictions"])
            pool_apy_statistics = APYStatistics(
                mu=pool["mu"], sigma=pool["sigma"], count=pool["count"]
            )
            update_time = datetime.utcnow().isoformat()
            pool_metadata = await PoolsMetdadata.find_one(
                PoolsMetdadata.defillama_id == pool["pool"]
            )
            pool_snapshot = PoolsSnapshot(
                id=hasher.get_hash(f"{pool['symbol']}-{pool['project']}-{update_time}"),
                chain=pool["chain"],
                update_at=update_time,
                project=pool["project"],
                symbol=pool["symbol"],
                pool_name=pool_metadata.final_name if pool_metadata else pool["pool"],
                predictions=pool_predictions,
                apy_statistics=pool_apy_statistics,
                pool_charts_30d=pool_charts_30d,
            )
            _ = await pool_snapshot.save()
            logger.info(f"Saved snapshot for pool {pool['pool']}.")
    except (GenericServiceError, FailedExternalAPI) as e:
        logger.error(f"Error fetching pools data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(aggregate_solana_stable_pools())
