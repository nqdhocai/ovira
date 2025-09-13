from pydantic import BaseModel


class SuccessResponse(BaseModel):
    status_code: int
    message: str
