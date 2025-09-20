import asyncio
import logging
from typing import Any

from api.models import SupportedTokens
from beanie import init_beanie
from config.settings import databases_config
from database.models import (
    AgentMessages,
    PoolsMetdadata,
    PoolSnapshot,
    PoolSnapshotMinimal,
)
from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from utils.singleton_base import SingletonBase

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TVL_THRESHOLD = 20000


class MongoDB(SingletonBase):
    def __init__(self):
        self.client: AsyncMongoClient[Any] = AsyncMongoClient(
            databases_config.MONGO_DB_URI, uuidRepresentation="standard"
        )
        self.db: AsyncDatabase[Any] = self.client[databases_config.MONGO_DB_NAME]

    async def init(self):
        await init_beanie(
            database=self.db,
            document_models=[PoolSnapshot, PoolsMetdadata, AgentMessages],
        )

    async def get_all_pools(self) -> list[PoolSnapshot]:
        return await PoolSnapshot.find_all().to_list()

    async def get_pool_by_symbol(self, symbol: str) -> list[PoolSnapshot]:
        return await PoolSnapshot.find(PoolSnapshot.symbol == symbol).to_list()

    async def get_latest_pools(self):
        return (
            await PoolSnapshot.find()
            .sort((PoolSnapshot.update_at, DESCENDING))  # pyright: ignore[reportArgumentType]
            .to_list()
        )

    async def get_latest_pool_by_name(self, pool_name: str) -> PoolSnapshot | None:
        return (
            await PoolSnapshot.find(PoolSnapshot.pool_name == pool_name)
            .sort(
                (PoolSnapshot.update_at, DESCENDING)  # pyright: ignore[reportArgumentType]
            )
            .first_or_none()
        )

    async def _get_pools_name_by_symbol(self, symbol: SupportedTokens) -> list[str]:
        return [
            p.final_name
            for p in await PoolsMetdadata.find(
                PoolsMetdadata.symbol == symbol
            ).to_list()
        ]

    async def get_latest_pools_by_symbol(
        self, symbol: SupportedTokens
    ) -> list[PoolSnapshotMinimal]:
        pool_names = await self._get_pools_name_by_symbol(symbol)
        tasks = [self.get_latest_pool_by_name(name) for name in pool_names]

        results = await asyncio.gather(*tasks)
        return [
            PoolSnapshotMinimal(
                pool_name=r.pool_name,
                apy_statistics=r.apy_statistics,
                apyPct1D=r.apyPct1D,
                apyPct7D=r.apyPct7D,
                apyPct30D=r.apyPct30D,
                tvlUsd=r.tvlUsd,
                apy=r.apy,
            )
            for r in results
            if r is not None
            and r.apy is not None
            and r.tvlUsd is not None
            and r.tvlUsd > TVL_THRESHOLD
        ]

    async def insert_agent_messages(self, messages: list[AgentMessages]) -> None:
        _ = await AgentMessages.insert_many(messages)

    async def get_reasoning_trace(self, thread_id: str) -> list[AgentMessages]:
        return (
            await AgentMessages.find(AgentMessages.thread_id == thread_id)
            .sort((AgentMessages.timestamp, ASCENDING))
            .to_list()
        )


async def main():
    import json

    mongo = MongoDB()
    await mongo.init()
    pool = await mongo.get_latest_pool_by_name("USDC kamino-lend")
    print(pool)
    print(f"Total pools: {len(pool)}")

    with open("pools.json", "w") as f:
        json.dump([p.model_dump() for p in pool[:5]], f, default=str)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
