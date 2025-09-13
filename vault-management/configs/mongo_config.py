from pydantic import BaseModel


class MongoConfig(BaseModel):
    uri: str
    db_name: str
