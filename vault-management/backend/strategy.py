from datetime import datetime
from typing import Any

from clients import Clients
from configs import get_logger
from hooks.error import ResourceNotFound
from llm.strategy_updated import get_strategy_changes
from mongo.schemas import (
    PoolsSnapshot,
    StrategyInfo,
    UpdatedInfo,
    VaultsMetadata,
    VaultsStrategy,
    VaultsUpdated,
)
from utils import hasher

logger = get_logger("strategy_operations")
mongo_client = Clients.get_mongo_client()


class StrategyOperations:
    def __init__(self, strategy_info: StrategyInfo, vault_name: str):
        self.strategy_response: StrategyInfo = strategy_info
        self.vault_name: str = vault_name

    async def get_chosen_pool_apy(self, pool_name: str) -> float:
        pool = (
            await PoolsSnapshot.find(PoolsSnapshot.pool_name == pool_name)
            .sort(-PoolsSnapshot.update_at)
            .first_or_none()
        )
        if pool:
            last_snapshot = pool.pool_charts_30d[-1]
            return last_snapshot.apy
        else:
            logger.warning(f"Pool with name {pool_name} not found.")
            raise ResourceNotFound(f"Pool with name {pool_name} not found.")

    def get_vault_apy(self, pools_allocation: list[tuple[float, float]]) -> float:
        vault_apy = sum(apy * weight for apy, weight in pools_allocation)
        return vault_apy

    async def upload_vault_data(self):
        vault: VaultsMetadata | None = await VaultsMetadata.find_one(
            VaultsMetadata.name == self.vault_name
        )
        if not vault:
            raise ResourceNotFound(f"Vault with name {self.vault_name} not found.")
        pools_allocation: list[tuple[float, float]] = []
        for allocation in self.strategy_response.strategy.allocations:
            try:
                pool_apy = await self.get_chosen_pool_apy(allocation.pool_name)
                pools_allocation.append((pool_apy, allocation.weight_pct / 100))
            except ResourceNotFound as e:
                logger.error(f"Error getting APY for pool {allocation.pool_name}: {e}")
                raise ResourceNotFound(
                    f"Error getting APY for pool {allocation.pool_name}: {e}"
                )
        vault_apy = self.get_vault_apy(pools_allocation)
        update_time = datetime.utcnow().isoformat()
        # Save Strategy Data
        vault_data = VaultsStrategy(
            id=hasher.get_hash(f"{vault.id}-{update_time}"),
            update_at=update_time,
            vault=vault,
            apy=vault_apy,
            strategy=self.strategy_response,
        )
        _ = await vault_data.save()
        logger.info(f"Vault strategy data saved for vault {vault.name}.")
        # Save Updated Info
        lastest_strategy: VaultsStrategy | None = (
            await VaultsStrategy.find(VaultsStrategy.vault.id == vault.id)
            .sort(-VaultsStrategy.update_at)
            .first_or_none()
        )
        if lastest_strategy:
            try:
                last_updated = VaultsUpdated(
                    id=hasher.get_hash(f"{vault.name}-{update_time}-updated"),
                    update_at=update_time,
                    vault=vault,
                    last_updated=get_strategy_changes(vault_data, lastest_strategy),
                )
                _ = await last_updated.save()
                logger.info(
                    f"Vault {vault.name} strategy updated. Changes: {last_updated.last_updated}"
                )
            except Exception as e:
                logger.error(f"Error updating info for vault {vault.name}: {e}")
                raise
        else:
            logger.info(f"No previous strategy found for vault {vault.name}.")
            last_updated = VaultsUpdated(
                id=hasher.get_hash(f"{vault.name}-{update_time}-updated"),
                update_at=update_time,
                vault=vault,
                last_updated=UpdatedInfo(
                    action="Initial Strategy",
                    details="First strategy entry for the vault",
                ),
            )
            _ = await last_updated.save()
        logger.info("Vault strategy data uploaded successfully.")
