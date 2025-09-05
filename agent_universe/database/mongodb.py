import threading

from beanie import init_beanie
from config.settings import databases_config
from models import ProtocolDoc  # Adjust the import based on your project structure
from pymongo import AsyncMongoClient


class MongoDB:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MongoDB, cls).__new__(cls)
        return cls._instance

    async def init(self):
        self.client = AsyncMongoClient(databases_config.MONGO_DB_URI)
        self.db = self.client[databases_config.MONGO_DB_NAME]
        await init_beanie(database=self.db, document_models=[ProtocolDoc])

    async def get_all_latest_protocols(self) -> list[ProtocolDoc] | None:
        pipeline = [
            {"$sort": {"timestamp": -1}},  # Sort by timestamp descending
            {
                "$group": {
                    "_id": "$protocol",
                    "doc": {"$first": "$$ROOT"},
                }
            },
            {"$replaceRoot": {"newRoot": "$doc"}},  # Replace root with the document
        ]
        results: list[ProtocolDoc] = (
            await ProtocolDoc.find_many().aggregate(pipeline, ProtocolDoc).to_list()
        )
        return results if results else None

    async def get_latest_protocol_by_name(
        self, protocol_name: str
    ) -> ProtocolDoc | None:
        pipeline = [
            {"$match": {"protocol": protocol_name}},  # Filter by protocol name
            {"$sort": {"timestamp": -1}},  # Sort by timestamp descending
            {"$limit": 1},  # Get the latest document
        ]
        result: list[ProtocolDoc] = (
            await ProtocolDoc.find_many().aggregate(pipeline, ProtocolDoc).to_list()
        )
        return result[0] if result else None
