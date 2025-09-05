import asyncio

from clients import Clients
from configs import get_logger
from data_aggregator.aggregator import aggregate_protocol_snapshot_data
from data_aggregator.fetching_data import fetch_and_store_defillama_data
from prefect import flow, task
from prefect.futures import wait

logger = get_logger("prefect-monitors")
mongo_client = Clients.get_mongo_client()


@task(name="Aggregate Protocol Snapshot Data")
async def aggregate_data():
    logger.info("Starting data aggregation task...")
    try:
        logger.info("Fetching data before aggregation...")
        await fetch_and_store_defillama_data()
        logger.info("Data fetching completed. Starting aggregation...")
        await aggregate_protocol_snapshot_data()
        logger.info("Data aggregation task completed successfully.")
    except Exception as e:
        logger.error(f"Data aggregation task failed: {e}")
        raise


@flow(
    name="DeFi Data Pipeline",
    description="Fetches data from DeFiLlama and aggregates protocol snapshots each 1h.",
    log_prints=True,
)
async def defi_data_pipeline():
    # await mongo_client.initialize()
    try:
        logger.info("Starting DeFi data pipeline...")
        _ = await aggregate_data()
        logger.info("DeFi data pipeline completed.")
    except Exception as e:
        logger.error(f"DeFi data pipeline failed: {e}")
        raise
    # finally:
    #     await mongo_client.close()
