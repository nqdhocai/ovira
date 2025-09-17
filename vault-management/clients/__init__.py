from configs import get_logger

logger = get_logger("clients")

from clients.aiohttp import HTTPRequestClient
from clients.mongo_client import MongoClient


class Clients:
    _http_client: HTTPRequestClient | None = None
    _mongo_client: MongoClient | None = None

    @classmethod
    def get_mongo_client(cls) -> MongoClient:
        if not cls._mongo_client:
            cls._mongo_client = MongoClient()
        return cls._mongo_client

    @classmethod
    def get_http_client(cls) -> HTTPRequestClient:
        if not cls._http_client:
            cls._http_client = HTTPRequestClient()
        return cls._http_client

    @classmethod
    async def startup(cls):
        if not cls._http_client:
            cls._http_client = HTTPRequestClient()

        await cls._http_client.startup()

    @classmethod
    async def close(cls):
        if cls._http_client:
            await cls._http_client.close()
