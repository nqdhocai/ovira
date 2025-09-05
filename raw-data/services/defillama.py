from typing import Any

from configs import get_logger
from hooks.error import FailedExternalAPI, GenericServiceError
from services.http_request import HTTPClient, HTTPMethod

logger = get_logger("defillama")


class DeFiLlama:
    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client

    async def async_get_request(
        self,
        url: str,
        method: HTTPMethod = HTTPMethod.GET,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, any] | Any:
        try:
            response = await self.http_client.get_response_async(
                url, method=method, params=params
            )
            return response
        except (GenericServiceError, FailedExternalAPI) as e:
            logger.error(f"DeFiLlama async_get_request error: {e}")
            raise
        except Exception as e:
            logger.error(f"DeFiLlama async_get_request unexpected error: {e}")
            raise
