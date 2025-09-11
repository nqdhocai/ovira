import asyncio

from clients import Clients
from configs import get_logger
from data_aggregator.aggregator import aggregate_solana_stable_pools
from prefect import flow, task
from prefect.futures import wait

logger = get_logger("prefect-monitors")
mongo_client = Clients.get_mongo_client()


@task(name="Aggregate Protocol Snapshot Data")
async def aggregate_data():
    logger.info("Starting data aggregation task...")
    try:
        await aggregate_solana_stable_pools()
        logger.info("Data aggregation task completed successfully.")
    except Exception as e:
        logger.error(f"Data aggregation task failed: {e}")
        raise


@flow(
    name="DeFi Data Pipeline",
    description="Fetches data from DeFiLlama and aggregates protocol snapshots each 3h.",
    log_prints=True,
)
async def defi_data_pipeline():
    try:
        logger.info("Starting DeFi data pipeline...")
        _ = await aggregate_data()
        logger.info("DeFi data pipeline completed.")
    except Exception as e:
        logger.error(f"DeFi data pipeline failed: {e}")
        raise
