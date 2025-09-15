import asyncio
from datetime import datetime

from clients import Clients
from configs import get_logger, vault_management_config
from hooks.error import FailedExternalAPI, GenericServiceError
from mongo.schemas import UserBalanceHistory, UserMetadata, VaultsMetadata
from services.http_request import HTTPMethod

aiohttp_client = Clients().get_http_client().get_http_client()

logger = get_logger("earnings_updating")


class EarningsUpdating:
    @staticmethod
    async def update_user_earnings(
        user_wallet: str, vault_name: str, time_interval: float = 6.0
    ):
        logger.info(f"Updating earnings for user: {user_wallet} in vault: {vault_name}")
        endpoint = f"http://{vault_management_config.url}:{vault_management_config.port}/user/balance/update_earnings"
        payload = {
            "user_wallet": user_wallet,
            "vault_name": vault_name,
            "time_interval": time_interval,
        }
        try:
            response = await aiohttp_client.get_response_async(
                method=HTTPMethod.POST, url=endpoint, data=payload
            )
            logger.info(f"Earnings updated for user {user_wallet}: {response}")
        except (GenericServiceError, FailedExternalAPI) as e:
            logger.error(f"Error updating earnings for user {user_wallet}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

    @staticmethod
    async def update_all_users_earnings():
        users = await UserMetadata.find_all().to_list()
        for user in users:
            user_balance = (
                await UserBalanceHistory.find(UserBalanceHistory.user.id == user.id)
                .sort(-UserBalanceHistory.update_at)
                .first_or_none()
            )
            if user_balance:
                vault = await VaultsMetadata.find_one(
                    VaultsMetadata.id == user_balance.vault.id
                )
                if vault:
                    _ = asyncio.create_task(
                        EarningsUpdating.update_user_earnings(
                            user.wallet_address, vault.name
                        )
                    )
                    await asyncio.sleep(1)  # To avoid overwhelming the server
