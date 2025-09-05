from clients.services import Services
from services.defillama import DeFiLlama


class ServicesClient:
    _defillama_client: DeFiLlama | None = None

    @classmethod
    def get_defillama_client(cls) -> DeFiLlama:
        if not cls._defillama_client:
            cls._defillama_client = Services.get_defillama_client()
        return cls._defillama_client
