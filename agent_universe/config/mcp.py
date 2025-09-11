from pydantic import BaseModel

from config import root_config


class MCPConfig(BaseModel):
    CORAL_SSE_URL: str = root_config.mcp.coral_protocol.sse_url
    TIMEOUT_MS: int | None = root_config.mcp.coral_protocol.timeout_ms
