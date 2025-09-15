import asyncio
from typing import Any

from api.models import SupportedTokens
from beanie import init_beanie
from config.settings import databases_config
from database.models import PoolsMetdadata, PoolSnapshot
from pymongo import DESCENDING, AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from utils.singleton_base import SingletonBase


class MongoDB(SingletonBase):
    def __init__(self):
        self.client: AsyncMongoClient[Any] = AsyncMongoClient(
            databases_config.MONGO_DB_URI, uuidRepresentation="standard"
        )
        self.db: AsyncDatabase[Any] = self.client[databases_config.MONGO_DB_NAME]

    async def init(self):
        await init_beanie(
            database=self.db, document_models=[PoolSnapshot, PoolsMetdadata]
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
            .limit(1)
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
    ) -> list[PoolSnapshot]:
        pool_names = await self._get_pools_name_by_symbol(symbol)
        tasks = [self.get_latest_pool_by_name(name) for name in pool_names]

        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]


async def main():
    import json

    mongo = MongoDB()
    await mongo.init()
    pool = await mongo.get_latest_pools_by_symbol("USDC")
    print(f"Total pools: {len(pool)}")

    with open("pools.json", "w") as f:
        json.dump([p.model_dump() for p in pool[:5]], f, default=str)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
