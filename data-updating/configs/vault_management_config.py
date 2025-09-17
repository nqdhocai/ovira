from pydantic import BaseModel


class VaultManagementConfig(BaseModel):
    url: str
    port: int
