from configs import get_logger
from hooks.error import ResourceNotFound
from mongo.schemas import UserBalanceHistory, UserMetadata, VaultsMetadata
from utils import hasher

logger = get_logger("user_operations")


class UserOperations:
    @staticmethod
    async def create_user(wallet_address: str) -> UserMetadata:
        existing_user = await UserMetadata.find_one(
            UserMetadata.wallet_address == wallet_address
        )
        if existing_user:
            raise ResourceNotFound(f"User with wallet {wallet_address} already exists.")
        else:
            new_user = UserMetadata(
                id=hasher.get_hash(wallet_address), wallet_address=wallet_address
            )
            _ = await new_user.save()
            logger.info(f"User with wallet {wallet_address} created successfully.")
            return new_user

    @staticmethod
    async def get_user_balance(user_wallet: str, vault_name: str) -> float:
        user = await UserMetadata.find_one(UserMetadata.wallet_address == user_wallet)
        if not user:
            raise ResourceNotFound(f"User with wallet {user_wallet} not found.")
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        user_balance = await UserBalanceHistory.find_one(
            And(
                UserBalanceHistory.user == user.id,
                UserBalanceHistory.vault == vault.id,
            ),
            sort=[("update_at", -1)],
        )
        return user_balance.balance if user_balance else 0.0
