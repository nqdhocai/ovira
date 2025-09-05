from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    uri: str
    db_name: str


class RootConfig(BaseModel):
    mongodb: DatabaseConfig
