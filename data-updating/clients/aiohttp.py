from services.http_request import HTTPClient


class HTTPRequestClient:
    _http_client: HTTPClient | None = None

    @classmethod
    def get_http_client(cls) -> HTTPClient:
        if not cls._http_client:
            cls._http_client = HTTPClient()
        return cls._http_client

    @classmethod
    async def startup(cls) -> None:
        if not cls._http_client:
            cls._http_client = HTTPClient()

        await cls._http_client.init_sessions()

    @classmethod
    async def close(cls) -> None:
        if cls._http_client:
            await cls._http_client.close_sessions()
