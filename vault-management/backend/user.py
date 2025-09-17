from datetime import datetime

from beanie.operators import And

from configs import get_logger
from hooks.error import ResourceNotFound
from mongo.schemas import (
    UserBalanceHistory,
    UserMetadata,
    VaultsMetadata,
    VaultsStrategy,
)
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
    async def get_user_balance_nav(user_wallet: str, vault_name: str) -> float:
        user = await UserMetadata.find_one(UserMetadata.wallet_address == user_wallet)
        if not user:
            raise ResourceNotFound(f"User with wallet {user_wallet} not found.")
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        user_balance = (
            await UserBalanceHistory.find(
                And(
                    UserBalanceHistory.user.id == user.id,
                    UserBalanceHistory.vault.id == vault.id,
                )
            )
            .sort(-UserBalanceHistory.update_at)
            .first_or_none()
        )
        return (
            user_balance.remaining_banlance + user_balance.earnings
            if user_balance
            else 0.0
        )

    @staticmethod
    async def get_user_balance_earnings(user_wallet: str, vault_name: str) -> float:
        user = await UserMetadata.find_one(UserMetadata.wallet_address == user_wallet)
        if not user:
            raise ResourceNotFound(f"User with wallet {user_wallet} not found.")
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        user_balance = (
            await UserBalanceHistory.find(
                And(
                    UserBalanceHistory.user.id == user.id,
                    UserBalanceHistory.vault.id == vault.id,
                )
            )
            .sort(-UserBalanceHistory.update_at)
            .first_or_none()
        )
        return user_balance.earnings if user_balance else 0.0

    @staticmethod
    async def update_user_balance_earnings(
        user_wallet: str, vault_name: str, time_interval: float = 6.0
    ):
        user = await UserMetadata.find_one(UserMetadata.wallet_address == user_wallet)
        if not user:
            raise ResourceNotFound(f"User with wallet {user_wallet} not found.")
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        vault_strategy = (
            await VaultsStrategy.find(VaultsStrategy.vault.id == vault.id)
            .sort(-VaultsStrategy.update_at)
            .first_or_none()
        )
        if not vault_strategy:
            raise ResourceNotFound(f"Vault strategy for {vault_name} not found.")

        user_balance = (
            await UserBalanceHistory.find(
                And(
                    UserBalanceHistory.user.id == user.id,
                    UserBalanceHistory.vault.id == vault.id,
                )
            )
            .sort(-UserBalanceHistory.update_at)
            .first_or_none()
        )
        if not user_balance:
            raise ResourceNotFound(
                f"No balance record found for user {user_wallet} in vault {vault_name}."
            )
        # Simple interest calculation for demonstration purposes
        interest_rate = vault_strategy.apy
        earnings = (
            user_balance.remaining_banlance * (interest_rate / 365 / 24) * time_interval
        )
        updated_time = datetime.utcnow().isoformat()
        new_user_balance = UserBalanceHistory(
            id=hasher.get_hash(f"{user.id}-{vault.id}-{updated_time}-earnings"),
            user=user,
            vault=vault,
            remaining_banlance=user_balance.remaining_banlance,
            earnings=user_balance.earnings + earnings,
            update_at=updated_time,
        )
        _ = await user_balance.save()
        logger.info(
            f"User {user_wallet} earnings in vault {vault_name} updated by {earnings:.4f}."
        )
