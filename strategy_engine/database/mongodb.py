from typing import Any

from beanie import init_beanie
from config.settings import databases_config
from database.models import PoolSnapshot
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from utils.singleton_base import SingletonBase


class MongoDB(SingletonBase):
    def __init__(self):
        self.client: AsyncMongoClient[Any] = AsyncMongoClient(
            databases_config.MONGO_DB_URI, uuidRepresentation="standard"
        )
        self.db: AsyncDatabase[Any] = self.client[databases_config.MONGO_DB_NAME]

    async def init(self):
        await init_beanie(database=self.db, document_models=[PoolSnapshot])

    async def get_all_pools(self) -> list[PoolSnapshot]:
        return await PoolSnapshot.find_all().to_list()


async def main():
    import json

    mongo = MongoDB()
    await mongo.init()
    pools = await mongo.get_all_pools()
    print(pools[0])
    print(f"Total pools: {len(pools)}")

    with open("pools.json", "w") as f:
        json.dump([p.model_dump() for p in pools[:5]], f, default=str)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
