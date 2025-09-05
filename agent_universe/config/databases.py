from pydantic import BaseModel

from config import root_config


class DatabaseConfig(BaseModel):
    MONGO_DB_URI: str = root_config.mongodb.uri
    MONGO_DB_NAME: str = root_config.mongodb.db_name
