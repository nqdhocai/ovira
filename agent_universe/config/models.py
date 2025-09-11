from pydantic import BaseModel


class DatabaseBase(BaseModel):
    uri: str
    db_name: str


class MCPBase(BaseModel):
    sse_url: str
    timeout_ms: int | None = None


class ModelBase(BaseModel):
    provider: str
    api_key: str
    api_version: str | None = None
    base_url: str | None = None
    model_name: str
    temperature: float
    max_tokens: int


class AgentConfig(BaseModel):
    llm_model: ModelBase


class MCPConfig(BaseModel):
    coral_protocol: MCPBase


class DatabasesConfig(BaseModel):
    mongodb: DatabaseBase


class RootConfig(BaseModel):
    databases: DatabasesConfig
    mcp: MCPConfig
    agents: AgentConfig
