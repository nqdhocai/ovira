from __future__ import annotations

import json
from enum import Enum
from typing import Any

import aiohttp
import ujson
from aiohttp import ClientError, ClientSession, ClientTimeout
from requests import Session
from requests.exceptions import RequestException

from configs import get_logger
from hooks.error import (
    FailedExternalAPI,
    GenericServiceError,
    ServicesAuthenticationError,
)
from services.base_singleton import SingletonMeta

logger = get_logger("http_client")


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HTTPClient(metaclass=SingletonMeta):
    _instance: HTTPClient | None = None
    _aiohttp_session: ClientSession | None = None
    _requests_session: Session | None = None
    _max_retries: int = 1

    @classmethod
    def get_instance(cls) -> HTTPClient:
        instance = cls()
        return instance

    async def get_aiohttp_session(self) -> ClientSession:
        if self._aiohttp_session is None or self._aiohttp_session.closed:
            timeout = ClientTimeout(total=300)
            self._aiohttp_session = aiohttp.ClientSession(timeout=timeout)
        return self._aiohttp_session

    def get_requests_session(self) -> Session:
        if self._requests_session is None:
            self._requests_session = Session()
        return self._requests_session

    async def init_sessions(self):
        _ = await self.get_aiohttp_session()
        _ = self.get_requests_session()

    async def close_sessions(self):
        if self._aiohttp_session and not self._aiohttp_session.closed:
            await self._aiohttp_session.close()
            self._aiohttp_session = None
        if self._requests_session:
            self._requests_session.close()
            self._requests_session = None

    @staticmethod
    def _handle_response_error(status: int | None, url: str, response_data: Any):
        message: str
        if isinstance(response_data, dict):
            raw_message = (  # pyright: ignore[reportUnknownVariableType]
                response_data.get("message")  # pyright: ignore[reportUnknownMemberType]
                or response_data.get("error")
                or response_data.get("detail")
                or str(response_data)
            )
            message = str(raw_message)  # pyright: ignore[reportUnknownArgumentType]
        else:
            message = str(response_data)
        if status and 200 <= status < 300:
            return
        elif status == 401:
            logger.error(f"401 Unauthorized at {url}: {message}")
            raise ServicesAuthenticationError(message)
        elif status:
            logger.error(f"Error {status} at {url}: {message}")
            raise GenericServiceError(
                status_code=status,
                message=message,
            )
        else:
            logger.error(f"Failed to get response from {url}: {message}")
            raise FailedExternalAPI(
                f"Failed to receive response status from service: {message}"
            )

    def get_response(
        self,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        method: HTTPMethod = HTTPMethod.GET,
    ) -> dict[str, Any] | list[Any] | Any:
        """Get the response synchronously from a specified URL

        Args:
            url (str): The API URL.
            method (HTTPMethod): HTTP method.
            headers (dict): Request headers including authorization.
            params (dict, optional): Query parameters. Defaults to dict empty.
            data (dict, optional): JSON payload for POST requests. Defaults to dict empty.

        Raises:
            FailedExternalAPI: If API call fails.

        Returns:
            dict: The response data.
        """
        params = self._normalize_params(params or {})
        if data is None:
            data = {}

        session = self.get_requests_session()
        session.headers.update(headers)
        for attempt in range(1, self._max_retries + 1):
            try:
                if method == HTTPMethod.GET:
                    response = session.get(url, params=params)
                elif method == HTTPMethod.POST:
                    response = session.post(url, params=params, json=data)
                elif method == HTTPMethod.PUT:
                    response = session.put(url, params=params, json=data)
                elif method == HTTPMethod.DELETE:
                    response = session.delete(url, params=params)

                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    raise FailedExternalAPI(f"Invalid JSON response from {url}")

                self._handle_response_error(response.status_code, url, response_data)
                return response_data

            except RequestException as e:
                logger.error(
                    f"[Attempt {attempt}] Sync HTTP request to {url} failed: {e}"
                )
                if attempt >= self._max_retries:
                    raise FailedExternalAPI(
                        f"Sync HTTP request to {url} failed after {self._max_retries} retries: {e}"
                    )

    async def get_response_async(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        method: HTTPMethod = HTTPMethod.GET,
    ) -> dict[str, Any] | list[Any] | Any:
        """Get the response asynchronously from a specified URL

        Args:
            url (str): The API URL.
            method (HTTPMethod): HTTP method.
            headers (dict): Request headers including authorization.
            params (dict, optional): Query parameters. Defaults to dict empty.
            data (dict, optional): JSON payload for POST requests. Defaults to dict empty.

        Raises:
            FailedExternalAPI: If API call fails.

        Returns:
            dict: The response data.
        """
        params = self._normalize_params(params or {})

        if data is None:
            data = {}

        session = await self.get_aiohttp_session()
        for attempt in range(1, self._max_retries + 1):
            try:
                if method == HTTPMethod.GET:
                    async with session.get(
                        url, headers=headers, params=params
                    ) as response:
                        response_data = await response.json()
                elif method == HTTPMethod.POST:
                    async with session.post(
                        url, headers=headers, params=params, json=data
                    ) as response:
                        response_data = await response.json()
                elif method == HTTPMethod.PUT:
                    async with session.put(
                        url, headers=headers, params=params, json=data
                    ) as response:
                        response_data = await response.json()
                elif method == HTTPMethod.DELETE:
                    async with session.delete(
                        url, headers=headers, params=params
                    ) as response:
                        response_data = await response.json()

                self._handle_response_error(response.status, url, response_data)
                return response_data

            except ClientError as e:
                logger.error(
                    f"[Attempt {attempt}] Async HTTP request to {url} failed: {e}"
                )
                if attempt >= self._max_retries:
                    raise FailedExternalAPI(
                        f"Async HTTP request to {url} failed after {self._max_retries} retries: {e}"
                    )

    @staticmethod
    def _normalize_params(params: dict[str, Any]) -> dict[str, str]:
        """
        Convert all values in a dict to str, suitable for aiohttp query params.
        - bool → "true"/"false"
        - dict/list → JSON string
        - None → skip
        - others → str(value)
        """
        result: dict[str, str] = {}

        for k, v in params.items():
            if v is None:
                continue
            elif isinstance(v, bool):
                result[k] = str(v).lower()
            elif isinstance(v, (dict, list)):
                result[k] = ujson.dumps(v)
            else:
                result[k] = str(v)

        return result
