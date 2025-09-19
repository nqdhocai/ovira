import asyncio
import json
from datetime import datetime

from clients import Clients
from configs import get_logger, strategy_agent_config, vault_management_config
from hooks.error import FailedExternalAPI, GenericServiceError
from mongo.schemas import StrategyInfo, VaultsMetadata
from services.http_request import HTTPMethod

aiohttp_client = Clients().get_http_client().get_http_client()
mongo_client = Clients().get_mongo_client()

logger = get_logger("strategy_updating")

root_time = datetime(2025, 9, 15, 0, 0, 0)


class StrategyUpdating:
    @staticmethod
    async def get_new_vault_strategy(
        vault_name: str, token: str, risk_label: str, policy: str | None = None
    ) -> StrategyInfo:
        # Implement the strategy update logic here
        endpoint = f"http://{strategy_agent_config.url}:{strategy_agent_config.port}/vault/rebalance"
        payload = {
            "token": token,
            "risk_label": risk_label,
        }
        if policy:
            payload["policy"] = policy
        try:
            response = await aiohttp_client.get_response_async(
                method=HTTPMethod.GET, url=endpoint, params=payload
            )
            return StrategyInfo.model_validate(response)
        except (GenericServiceError, FailedExternalAPI) as e:
            logger.error(f"Error updating strategy for vault {vault_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error at get new strategy for {vault_name}: {repr(e)}"
            )
            raise

    @staticmethod
    async def update_vault_strategy(
        vault_name: str, token: str, risk_label: str, policy: str | None = None
    ):
        logger.info(f"Updating strategy for vault: {vault_name}")
        endpoint = f"http://{vault_management_config.url}:{vault_management_config.port}/strategy/update_vault_strategy?vault_name={vault_name}"
        try:
            new_strategy = await StrategyUpdating.get_new_vault_strategy(
                vault_name, token, risk_label, policy
            )
            # with open(f"strategy_{vault_name}.json", "w") as f:
            #     json.dump(new_strategy.model_dump(), f, indent=4)
            data = new_strategy.model_dump()
            # print(f"New strategy for vault {vault_name}: {data}")
            response = await aiohttp_client.get_response_async(
                method=HTTPMethod.POST, url=endpoint, data=data
            )
            logger.info(f"Strategy updated for vault {vault_name}: {response}")
        except (GenericServiceError, FailedExternalAPI) as e:
            logger.error(f"Error updating strategy for vault {vault_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error at update strategy for vault {vault_name}: {repr(e)}"
            )
            raise

    @staticmethod
    async def update_all_vault_strategy(update_time: datetime):
        await mongo_client.initialize()
        logger.info(f"Starting update of all vault strategies at {update_time}")
        vaults = await VaultsMetadata.find_all().to_list()
        tasks_failed: list[str] = []
        for vault in vaults:
            if (datetime.utcnow() - root_time).seconds % (
                vault.update_frequency * 3600
            ) > 1200:
                continue
            try:
                await StrategyUpdating.update_vault_strategy(
                    vault_name=vault.name,
                    token=vault.asset,
                    risk_label=vault.risk_label,
                    policy=vault.policy_prompt,
                )
                await asyncio.sleep(5)
            except Exception:
                tasks_failed.append(vault.name)
                continue
        logger.info(
            f"Completed update of all vault strategies with failures: {tasks_failed}"
        )
