from datetime import datetime

from beanie.operators import And
from pydantic import BaseModel

from configs import get_logger
from hooks.error import ResourceNotFound
from mongo.schemas import (
    UserBalanceHistory,
    UserMetadata,
    VaultsHistory,
    VaultsMetadata,
    VaultsStrategy,
)
from utils import hasher

logger = get_logger("user_operations")


class VaultData(BaseModel):
    vault_name: str
    apy: str
    tvl: str


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
                    UserBalanceHistory.user.id == user.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    UserBalanceHistory.vault.id == vault.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                )
            )
            .sort(-UserBalanceHistory.update_at)
            .first_or_none()
        )
        return (
            user_balance.remaining_balance + user_balance.earnings
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
            user_balance.remaining_balance * (interest_rate / 365 / 24) * time_interval
        )
        updated_time = datetime.utcnow().isoformat()
        new_user_balance = UserBalanceHistory(
            id=hasher.get_hash(f"{user.id}-{vault.id}-{updated_time}-earnings"),
            user=user,
            vault=vault,
            remaining_balance=user_balance.remaining_balance,
            earnings=user_balance.earnings + earnings,
            update_at=updated_time,
        )
        _ = await user_balance.save()
        logger.info(
            f"User {user_wallet} earnings in vault {vault_name} updated by {earnings:.4f}."
        )

    @staticmethod
    async def get_all_vaults(user_wallet: str) -> dict[int, VaultData]:
        user = await UserMetadata.find_one(UserMetadata.wallet_address == user_wallet)
        if not user:
            raise ResourceNotFound(f"User with wallet {user_wallet} not found.")
        all_vault_names = [
            vault.name for vault in await VaultsMetadata.find_all().to_list()
        ]
        list_vault_data: list[VaultData] = []
        for vault_name in all_vault_names:
            vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
            if not vault:
                continue
            user_balance = (
                await UserBalanceHistory.find(
                    And(
                        UserBalanceHistory.user.id == user.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportUnknownArgumentType, reportAttributeAccessIssue]
                        UserBalanceHistory.vault.id == vault.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    )
                )
                .sort(-UserBalanceHistory.update_at)  # pyright: ignore[reportOperatorIssue, reportUnknownArgumentType]
                .first_or_none()
            )
            if not user_balance:
                continue
            vault_strategy = (
                await VaultsStrategy.find(
                    And(
                        VaultsStrategy.user.id == user.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportUnknownArgumentType, reportAttributeAccessIssue]
                        VaultsStrategy.vault.id == vault.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    )
                )
                .sort(-VaultsStrategy.update_at)  # pyright: ignore[reportOperatorIssue, reportUnknownArgumentType]
                .first_or_none()
            )
            if not vault_strategy:
                continue
            vault_history = (
                await VaultsHistory.find(
                    And(
                        VaultsHistory.user.id == user.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportUnknownArgumentType, reportAttributeAccessIssue]
                        VaultsHistory.vault.id == vault.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    )
                )
                .sort(-VaultsHistory.update_at)  # pyright: ignore[reportOperatorIssue, reportUnknownArgumentType]
                .first_or_none()
            )
            if not vault_history:
                continue
            list_vault_data.append(
                VaultData(
                    vault_name=user_balance.vault.name,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    apy=vault_strategy.vault.apy,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    tvl=vault_history.vault.tvl,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportUnknownArgumentType, reportAttributeAccessIssue]
                )
            )
        list_vault_data.sort(key=lambda x: x.tvl, reverse=True)
        return {i: vault_data for i, vault_data in enumerate(list_vault_data)}
