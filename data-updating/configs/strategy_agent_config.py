from pydantic import BaseModel


class StrategyAgentConfig(BaseModel):
    url: str
    port: int
