from pydantic import BaseModel


class DatabaseBase(BaseModel):
    uri: str
    db_name: str


class DatabasesConfig(BaseModel):
    mongodb: DatabaseBase


class RootConfig(BaseModel):
    databases: DatabasesConfig
