from datetime import datetime
from typing import Any

from llm.gemini import get_strategy_changes

from clients import Clients
from configs import get_logger
from hooks.error import ResourceNotFound
from mongo.schemas import (
    PoolsSnapshot,
    StrategyInfo,
    VaultsMetadata,
    VaultsStrategy,
    VaultsUpdated,
)
from utils import hasher

logger = get_logger("strategy_operations")
mongo_client = Clients.get_mongo_client()


class StrategyOperations:
    def __init__(self, strategy_dict: dict[Any], vault_name: str):
        self.vault: VaultsMetadata | None = await VaultsMetadata.find_one(
            VaultsMetadata.name == vault_name
        )
        if not self.vault:
            raise ResourceNotFound(f"Vault with name {vault_name} not found.")
        self.strategy_response: StrategyInfo = StrategyInfo.model_validate(
            strategy_dict
        )

    async def get_chosen_pool_apy(self, pool_name) -> float:
        pool = await PoolsSnapshot.find_one(
            PoolsSnapshot.pool_name == pool_name, sort=[("update_at", -1)]
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
        # await mongo_client.initialize()
        pools_allocation = []
        for allocation in self.strategy_response.strategy.allocations:
            try:
                pool_apy = await self.get_chosen_pool_apy(allocation.pool_name)
                pools_allocation.append((pool_apy, allocation.weight / 100))
            except ResourceNotFound as e:
                logger.error(f"Error getting APY for pool {allocation.pool_name}: {e}")
                raise ResourceNotFound(
                    f"Error getting APY for pool {allocation.pool_name}: {e}"
                )
        vault_apy = self.get_vault_apy(pools_allocation)
        lastest_strategy = await VaultsStrategy.find_one(
            {"vault_name": "Ovira Vault"}, sort=[("update_at", -1)]
        )
        update_time = datetime.utcnow().isoformat()
        # Save Strategy Data
        vault_data = VaultsStrategy(
            id=hasher.get_hash(f"{self.vault.id}-{update_time}"),
            update_at=update_time,
            vault=self.vault,
            apy=vault_apy,
            strategy=self.strategy_response,
        )
        _ = await vault_data.save()
        # Save Updated Info
        if lastest_strategy:
            last_updated = VaultsUpdated(
                id=hasher.get_hash(f"{self.vault.id}-{update_time}-updated"),
                update_at=update_time,
                vault=self.vault,
                last_updated=get_strategy_changes(vault_data, lastest_strategy),
            )
            _ = await last_updated.save()
        logger.info("Vault strategy data uploaded successfully.")
