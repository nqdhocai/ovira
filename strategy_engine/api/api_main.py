import asyncio
import logging
from contextlib import asynccontextmanager

from agents.agents import start_agents_tasks
from api.models import StrategyResponse, SupportedTokens
from database.mongodb import MongoDB
from fastapi import FastAPI
from utils.models import RiskLabel

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
    global logger
    logger = logging.getLogger(__name__)
    mongo = MongoDB()
    await mongo.init()
    agent_tasks = await start_agents_tasks()

    try:
        yield
    finally:
        logger.info("Shutting down background agents...")
        for t in agent_tasks:
            _ = t.cancel()
        _ = await asyncio.gather(*agent_tasks, return_exceptions=True)
        logger.info("Closed connection")


app = FastAPI(root_path=API_PREFIX, lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/mongo-test")
async def mongo_test():
    mongo = MongoDB()
    try:
        pools = await mongo.get_all_pools()
        logger.info(f"Retrieved {len(pools)} pools from MongoDB")
        pools_data = [p.model_dump() for p in pools]
        logger.info(f"Sample pool data: {pools_data[0] if pools_data else 'No data'}")
        return {
            "status": "success",
            "total_pools": len(pools),
            "sample_pool": pools_data if pools_data else None,
        }
    except Exception as e:
        logger.error(f"Error in mongo_test: {e}")

        return {"status": "error", "error": str(e)}


@app.get("/vaults/rebalance")
async def get_vault_data(
    token: SupportedTokens, risk_label: RiskLabel, policy: str | None = None
) -> StrategyResponse:
    from api.rebalance_strategy import rebalance_strategy

    try:
        result = await rebalance_strategy(policy=policy, risk=risk_label, token=token)
        return StrategyResponse(status="success", error=None, strategy=result)
    except Exception as e:
        logger.error(f"Error in rebalance_strategy: {e}")
        return StrategyResponse(status="error", error=str(e), strategy=None)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
