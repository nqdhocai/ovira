import asyncio
from datetime import datetime

from prefect.futures import wait

from clients import Clients
from configs import get_logger
from data_aggregator.aggregator import aggregate_solana_stable_pools
from engine.earnings_updating import EarningsUpdating
from engine.strategy_updating import StrategyUpdating
from prefect import flow, task

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


@task(name="Update Strategy for All Vaults")
async def update_strategy_for_all_vaults():
    logger.info("Starting strategy update task...")
    try:
        await StrategyUpdating.update_all_vault_strategy(datetime.utcnow())
        logger.info("Strategy update task completed successfully.")
    except Exception as e:
        logger.error(f"Strategy update task failed: {e}")
        raise


@task(name="Update Earnings for All Users")
async def update_earnings_for_all_users():
    logger.info("Starting earnings update task...")
    try:
        await EarningsUpdating.update_all_users_earnings()
        logger.info("Earnings update task completed successfully.")
    except Exception as e:
        logger.error(f"Earnings update task failed: {e}")
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


@flow(
    name="Vaults Strategy Updater",
    description="Updates strategies for all vaults every 1h.",
)
async def vaults_strategy_updater():
    try:
        logger.info("Starting vaults strategy updater...")
        _ = await update_strategy_for_all_vaults()
        logger.info("Vaults strategy updater completed.")
    except Exception as e:
        logger.error(f"Vaults strategy updater failed: {e}")
        raise


@flow(
    name="User Earnings Updater",
    description="Updates earnings for all users every 6h.",
)
async def user_earnings_updater():
    try:
        logger.info("Starting user earnings updater...")
        _ = await update_earnings_for_all_users()
        logger.info("User earnings updater completed.")
    except Exception as e:
        logger.error(f"User earnings updater failed: {e}")
        raise
