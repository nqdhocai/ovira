from enum import Enum

from fastapi import HTTPException, status


class HTTPStatus(Enum):
    BAD_REQUEST = status.HTTP_400_BAD_REQUEST
    NOT_FOUND = status.HTTP_404_NOT_FOUND
    INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR


class BadAIResponse(HTTPException):
    def __init__(self, detail: str = "Bad response from AI Agents"):
        super().__init__(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value, detail=detail
        )
