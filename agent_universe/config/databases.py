from pydantic import BaseModel

from config import root_config


class DatabaseConfig(BaseModel):
    MONGO_DB_URI: str = root_config.databases.mongodb.uri
    MONGO_DB_NAME: str = root_config.databases.mongodb.db_name
