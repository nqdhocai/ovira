import logging
from typing import Any

from agents.models import FinalStrategyResponse
from agents.orchestrator import OrchestratorAgent
from api.models import SupportedTokens
from database.mongodb import MongoDB
from utils.models import RiskLabel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def rebalance_strategy(
    token: SupportedTokens,
    policy: str | dict[str, Any] | None = None,
    risk: RiskLabel = RiskLabel.BALANCED,
) -> FinalStrategyResponse:
    mongo = MongoDB()
    orchestrator = OrchestratorAgent()
    await orchestrator.initialize()

    pools = await mongo.get_latest_pools_by_symbol(token)

    logger.info(
        f"Fetched {len(pools)} pools from MongoDB | example: {pools[0] if pools else 'No pools found'}"
    )
    pools_data = [p.model_dump() for p in pools]
    for pool in pools_data:
        for key, value in pool.items():
            pool[key] = str(value) if value is not None else value

    logger.info(f"Total pools from DB: {len(pools_data)}")
    return await orchestrator.execute_strategy(
        pools_data=pools_data,
        policy=policy,
        risk=risk,
    )
