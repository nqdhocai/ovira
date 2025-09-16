from typing import Any

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from configs import get_logger, mongo_config
from mongo.schemas import DocumentModels
from services.base_singleton import SingletonMeta

logger = get_logger(__name__)


class MongoClient(metaclass=SingletonMeta):
    def __init__(self):
        self.client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(
            f"{mongo_config.uri}",
            uuidRepresentation="standard",
        )
        self.database: str = str(mongo_config.db_name)
        self.db: AsyncIOMotorDatabase[Any] = self.client[self.database]

    async def initialize(self):
        await init_beanie(
            self.db,
            document_models=DocumentModels,
        )
        logger.info("MongoDB client initialized.")

    async def close(self):
        self.client.close()
        logger.info("MongoDB client closed.")
