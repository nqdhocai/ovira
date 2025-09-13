from datetime import datetime

from beanie.operators import And

from configs import get_logger
from hooks.error import ResourceNotFound
from mongo.schemas import (
    Transaction,
    UserBalanceHistory,
    UserMetadata,
    VaultsHistory,
    VaultsMetadata,
)
from utils import hasher

from .user import UserOperations

logger = get_logger("strategy_operations")


class TransactionOperations:
    @staticmethod
    async def deposit(vault_name: str, amount: float, user_wallet: str):
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        user = await UserMetadata.find_one(UserMetadata.wallet_address == user_wallet)
        if not user:
            user = await UserOperations.create_user(user_wallet)
        transaction_time = datetime.utcnow().isoformat()
        vault_history = await VaultsHistory.find_one(
            VaultsHistory.vault == vault.id, sort=[("update_at", -1)]
        )
        # Update Vault History
        new_vault_history = VaultsHistory(
            id=hasher.get_hash(f"{vault.id}-{transaction_time}-deposit"),
            vault=vault,
            update_at=transaction_time,
            tvl=vault_history.tvl + amount if vault_history else amount,
        )
        _ = await new_vault_history.save()

        # Update User Balance
        user_balance = await UserBalanceHistory.find_one(
            And(
                UserBalanceHistory.user == user.id,
                UserBalanceHistory.vault == vault.id,
            ),
            sort=[("update_at", -1)],
        )
        new_user_balance = UserBalanceHistory(
            id=hasher.get_hash(f"{user.id}-{vault.id}-{transaction_time}-deposit"),
            user=user,
            vault=vault,
            balance=(user_balance.balance + amount) if user_balance else amount,
            update_at=transaction_time,
        )
        _ = await new_user_balance.save()

        # Record Transaction
        transaction = Transaction(
            id=hasher.get_hash(f"{vault.id}-{user.id}-{transaction_time}-deposit"),
            timestamp=transaction_time,
            vault=vault,
            user=user,
            type="deposit",
            amount=amount,
        )
        _ = await transaction.save()

        logger.info(
            f"Deposit of {amount} to vault {vault_name} by user {user_wallet} recorded successfully."
        )

    @staticmethod
    async def withdraw(vault_name: str, amount: float, user_wallet: str):
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        user = await UserMetadata.find_one(UserMetadata.wallet_address == user_wallet)
        if not user:
            raise ResourceNotFound(f"User with wallet {user_wallet} not found.")
        transaction_time = datetime.utcnow().isoformat()
        vault_history = await VaultsHistory.find_one(
            VaultsHistory.vault == vault.id, sort=[("update_at", -1)]
        )
        if not vault_history or vault_history.tvl < amount:
            raise ResourceNotFound(
                f"Insufficient funds in vault {vault_name} for withdrawal."
            )
        # Update Vault History
        new_vault_history = VaultsHistory(
            id=hasher.get_hash(f"{vault.id}-{transaction_time}-withdraw"),
            vault=vault,
            update_at=transaction_time,
            tvl=vault_history.tvl - amount,
        )
        _ = await new_vault_history.save()

        # Update User Balance
        user_balance = await UserBalanceHistory.find_one(
            And(
                UserBalanceHistory.user == user.id,
                UserBalanceHistory.vault == vault.id,
            ),
            sort=[("update_at", -1)],
        )
        if not user_balance or user_balance.balance < amount:
            raise ResourceNotFound(
                f"Insufficient balance for user {user_wallet} in vault {vault_name}."
            )
        new_user_balance = UserBalanceHistory(
            id=hasher.get_hash(f"{user.id}-{vault.id}-{transaction_time}-withdraw"),
            user=user,
            vault=vault,
            balance=user_balance.balance - amount,
            update_at=transaction_time,
        )
        _ = await new_user_balance.save()

        # Record Transaction
        transaction = Transaction(
            id=hasher.get_hash(f"{vault.id}-{user.id}-{transaction_time}-withdraw"),
            timestamp=transaction_time,
            vault=vault,
            user=user,
            type="withdrawal",
            amount=amount,
        )
        _ = await transaction.save()

        logger.info(
            f"Withdrawal of {amount} from vault {vault_name} by user {user_wallet} recorded successfully."
        )
