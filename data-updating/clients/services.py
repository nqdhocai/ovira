from clients.aiohttp import HTTPRequestClient
from services.defillama import DeFiLlama


class Services:
    @staticmethod
    def get_defillama_client() -> DeFiLlama:
        client = DeFiLlama(http_client=HTTPRequestClient.get_http_client())
        return client
