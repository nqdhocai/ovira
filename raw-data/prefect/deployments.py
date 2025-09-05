import asyncio
import traceback

import httpx

from prefect import aserve, flow
from prefect.client.schemas.schedules import CronSchedule
from prefect.monitors import defi_data_pipeline


async def create_work_pool():
    """Create work pool if not existing"""
    try:
        async with httpx.AsyncClient() as client:
            # Check if work pool exists
            response = await client.get(
                "http://prefect-server:4200/api/work_pools/ovira-pool"
            )
            if response.status_code == 200:
                print("Work pool 'ovira-pool' already exists")
                return

            # Create new work pool
            work_pool_data = {
                "name": "ovira-pool",
                "type": "process",
                "base_job_template": {},
                "description": "Ovira work pool for defi data pipeline",
            }

            response = await client.post(
                "http://prefect-server:4200/api/work_pools/", json=work_pool_data
            )

            if response.status_code in [200, 201]:
                print("Created work pool 'ovira-pool'")
            elif response.status_code == 409:
                print(f"Work pool 'ovira-pool' already exists")
            else:
                print(f"Failed to create work pool: {response.status_code}")

    except Exception as e:
        print(f"Error creating work pool: {e}")


async def deploy_flow():
    try:
        defi_data_pipeline_deployment = await defi_data_pipeline.to_deployment(
            name="defi-data-pipeline",
            tags=["defi", "data", "defillama", "protocols"],
            description="Fetches data from DeFiLlama and aggregates protocol snapshots.",
            schedule=CronSchedule(cron="0 * * * *"),  # Every hour
        )
        await aserve(defi_data_pipeline_deployment)
        print("Deployment created successfully.")
    except Exception as e:
        print(f"Error creating deployment: {e}")
        traceback.print_exc()


async def setup_prefect():
    """Setup dependencies for Prefect"""
    try:
        # Wait for Prefect server to be ready
        print("Waiting for Prefect server to start...")
        await asyncio.sleep(15)

        # Create work pool
        await create_work_pool()

        print("Setup successful! You can access http://localhost:4200 to run flows.")

    except Exception as e:
        print(f"Error during setup: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("Starting Prefect flow deployment...")
    asyncio.run(setup_prefect())
    print("Deploying flows...")
    asyncio.run(deploy_flow())
