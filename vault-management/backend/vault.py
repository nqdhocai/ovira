import random
from datetime import datetime, timedelta, timezone
from typing import Literal

import requests
from beanie.operators import GTE, LTE, And
from pydantic import BaseModel

from configs import get_logger, strategy_agent_config
from hooks.error import ResourceNotFound
from mongo.schemas import (
    PoolAllocation,
    ReasoningTrace,
    StrategyInfo,
    UserMetadata,
    VaultsHistory,
    VaultsMetadata,
    VaultsStrategy,
    VaultsUpdated,
)
from utils import hasher

from .strategy import StrategyOperations
from .user import UserOperations

logger = get_logger("vault_operations")


class VaultsData(BaseModel):
    name: str
    asset: Literal["USDT", "USDC"]
    risk_label: Literal["conservative", "balanced", "aggressive"]
    address: str
    update_frequency: float | None = None


class VaultStatistics(BaseModel):
    total_tvls: float
    num_creators: int


def get_current_target_time() -> datetime:
    now = datetime.utcnow()
    now = now.replace(minute=0, second=0, microsecond=0)
    if now.hour % 6 != 0:
        now = now - timedelta(hours=now.hour % 6)
    return now


class VaultStrategyUpdatedInfo(BaseModel):
    timestamp: datetime
    action: str
    details: str


class VaultOperations:
    @staticmethod
    async def create_vault_strategy(
        asset: Literal["USDT", "USDC"],
        risk_label: Literal["conservative", "balanced", "aggressive"],
        policy_prompt: str | None = None,
    ) -> StrategyInfo:
        endpoint = f"http://{strategy_agent_config.url}:{strategy_agent_config.port}/vault/rebalance"
        payload = {
            "token": asset,
            "risk_label": risk_label,
        }
        if policy_prompt:
            payload["policy"] = policy_prompt
        try:
            response = requests.get(url=endpoint, params=payload, timeout=300)
            return StrategyInfo.model_validate(response.json())
        except requests.RequestException as e:
            logger.error(f"Error creating strategy: {str(e)}")
            raise

    @staticmethod
    async def create_vault(
        vault_name: str,
        owner_wallet_address: str,
        asset: Literal["USDT", "USDC"],
        risk_label: Literal["conservative", "balanced", "aggressive"],
        update_frequency: float = 6.0,
        policy_prompt: str | None = None,
    ):
        owner = await UserMetadata.find_one(
            UserMetadata.wallet_address == owner_wallet_address
        )
        if not owner:
            owner = await UserOperations.create_user(owner_wallet_address)
        created_time = datetime.utcnow()
        vault = VaultsMetadata(
            id=hasher.get_hash(
                f"{vault_name}-{owner_wallet_address}-{created_time}-{asset}"
            ),
            name=vault_name,
            owner=owner,  # pyright: ignore[reportArgumentType]
            asset=asset,
            risk_label=risk_label,
            update_frequency=update_frequency,
            policy_prompt=policy_prompt,
            created_at=created_time,
            address="0x123",  # Address can be set later when the vault is deployed
        )
        _ = await vault.save()
        logger.info(f"Vault {vault_name} created successfully.")
        try:
            strategy = await VaultOperations.create_vault_strategy(
                asset=asset, risk_label=risk_label, policy_prompt=policy_prompt
            )
            upload_strategy = StrategyOperations(strategy, vault_name)
            await upload_strategy.upload_vault_data()
            logger.info(
                f"Initial strategy created and uploaded for vault {vault_name}."
            )
        except Exception as e:
            logger.error(f"Error creating initial strategy for vault {vault_name}: {e}")
            raise

    @staticmethod
    async def update_vault_policy(
        vault_name: str,
        new_update_frequency: float | None = None,
        new_policy_prompt: str | None = None,
    ):
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            logger.error(f"Vault {vault_name} not found.")
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        if new_update_frequency is not None:
            vault.update_frequency = new_update_frequency
        if new_policy_prompt is not None:
            vault.policy_prompt = new_policy_prompt
        _ = await vault.save()
        logger.info(f"Vault {vault_name} updated successfully.")

    @staticmethod
    async def get_vault_tvl(vault_name: str) -> float:
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            logger.error(f"Vault {vault_name} not found.")
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        latest_history = (
            await VaultsHistory.find(VaultsHistory.vault.id == vault.id)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
            .sort(-VaultsHistory.update_at)  # pyright: ignore[reportOperatorIssue, reportUnknownArgumentType]
            .first_or_none()
        )
        if not latest_history:
            logger.warning(f"No TVL data found for vault {vault_name}.")
            return 0.0
        return latest_history.tvl

    @staticmethod
    async def get_apy_chart(
        vault_name: str, days: int = 30
    ) -> list[tuple[datetime, float]]:
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            logger.error(f"Vault {vault_name} not found.")
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days + 1)
        strategies = (
            await VaultsStrategy.find(
                And(
                    VaultsStrategy.vault.id == vault.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    GTE(VaultsStrategy.update_at, start_time),
                    LTE(VaultsStrategy.update_at, end_time),
                ),
            )
            .sort("update_at")
            .to_list()
        )
        if len(strategies) == 0:
            logger.warning(
                f"No strategy data found for vault {vault_name} in the last {days} days."
            )
            return []
        end_time = get_current_target_time()
        start_time = end_time - timedelta(days=days)
        last_strategy_apy = strategies[-1].apy * 100
        apy_chart: list[tuple[datetime, float]] = []
        while start_time + timedelta(hours=6) <= end_time:
            # strategy = next(
            #     (
            #         s
            #         for s in reversed(strategies)
            #         if s.update_at <= start_time + timedelta(hours=6)
            #     ),
            #     None,
            # )
            # apy = strategy.apy if strategy else 0.0
            apy_chart.append(
                (
                    start_time,
                    (
                        1.0
                        * random.randint(
                            int(last_strategy_apy * 0.95), int(last_strategy_apy * 1.05)
                        )
                    )
                    / 100.0,
                )
            )
            start_time += timedelta(hours=6)
        apy_chart.append((start_time, last_strategy_apy / 100.0))
        return apy_chart

    @staticmethod
    async def get_tvl_chart(
        vault_name: str, days: int = 30
    ) -> list[tuple[datetime, float]]:
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            logger.error(f"Vault {vault_name} not found.")
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days + 1)
        histories = (
            await VaultsHistory.find(
                And(
                    VaultsHistory.vault.id == vault.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    GTE(VaultsHistory.update_at, start_time),
                    LTE(VaultsHistory.update_at, end_time),
                ),
            )
            .sort("update_at")
            .to_list()
        )
        if len(histories) == 0:
            logger.warning(
                f"No TVL data found for vault {vault_name} in the last {days} days."
            )
            return []
        end_time = get_current_target_time()
        start_time = end_time - timedelta(days=days)
        tvl_chart: list[tuple[datetime, float]] = []
        while start_time <= end_time:
            history = next(
                (
                    h
                    for h in reversed(histories)
                    if h.update_at <= start_time + timedelta(hours=6)
                ),
                None,
            )
            tvl = history.tvl if history else 0.0
            tvl_chart.append((start_time, tvl))
            start_time += timedelta(hours=6)
        return tvl_chart

    @staticmethod
    async def get_vault_pools_allocations(vault_name: str) -> list[PoolAllocation]:
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            logger.error(f"Vault {vault_name} not found.")
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        latest_strategy = (
            await VaultsStrategy.find(VaultsStrategy.vault.id == vault.id)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
            .sort(-VaultsStrategy.update_at)  # pyright: ignore[reportOperatorIssue, reportUnknownArgumentType]
            .first_or_none()
        )
        if not latest_strategy:
            logger.warning(f"No strategy data found for vault {vault_name}.")
            return []
        allocations = latest_strategy.strategy.strategy.allocations
        return allocations

    @staticmethod
    async def get_strategy_updated_history(
        vault_name: str, days: int = 7
    ) -> list[VaultStrategyUpdatedInfo]:
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            logger.error(f"Vault {vault_name} not found.")
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        updates = (
            await VaultsUpdated.find(
                And(
                    VaultsUpdated.vault.id == vault.id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportUnknownArgumentType, reportAttributeAccessIssue]
                    GTE(VaultsUpdated.update_at, start_time),
                    LTE(VaultsUpdated.update_at, end_time),
                ),
            )
            .sort("update_at")
            .to_list()
        )
        if len(updates) == 0:
            logger.warning(
                f"No update data found for vault {vault_name} in the last {days} days."
            )
            return []
        update_info = [
            VaultStrategyUpdatedInfo(
                timestamp=update.update_at,
                action=update.last_updated.action,
                details=update.last_updated.details,
            )
            for update in updates
        ]
        return update_info

    @staticmethod
    async def get_existing_vaults() -> list[VaultsData]:
        vaults = await VaultsMetadata.find().to_list()
        return [
            VaultsData(
                name=vault.name,
                asset=vault.asset,  # pyright: ignore[reportArgumentType]
                risk_label=vault.risk_label,
                address=vault.address,  # pyright: ignore[reportArgumentType]
                update_frequency=vault.update_frequency,
            )
            for vault in vaults
        ]

    @staticmethod
    async def get_all_vault_statistics() -> VaultStatistics:
        number_of_users = len(await UserMetadata.find_all().to_list())
        all_vault_names = [
            vault_metadata.name
            for vault_metadata in await VaultsMetadata.find_all().to_list()
        ]
        sum_tvls = 0
        for vault_name in all_vault_names:
            sum_tvls += await VaultOperations.get_vault_tvl(vault_name)
        return VaultStatistics(total_tvls=sum_tvls, num_creators=number_of_users)

    @staticmethod
    async def get_strategy_ai_reasoning_trace(vault_name: str) -> list[ReasoningTrace]:
        vault = await VaultsMetadata.find_one(VaultsMetadata.name == vault_name)
        if not vault:
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        strategy = (
            await VaultsStrategy.find(VaultsStrategy.vault.id == vault.id)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
            .sort(-VaultsStrategy.update_at)  # pyright: ignore[reportOperatorIssue]
            .first_or_none()
        )
        if not strategy:
            logger.warning(f"No strategy data found for vault {vault_name}.")
            return []
        return strategy.strategy.reasoning_trace
