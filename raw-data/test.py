import asyncio
import json
from datetime import datetime

from clients import Clients
from data_aggregator.aggregator import aggregate_protocol_snapshot_data
from data_aggregator.defillama_data import aggregate_defillama_data
from data_aggregator.derived_data import compute_derived_data
from utils.timestamp import floor_to_hour

mongo_client = Clients.get_mongo_client()


async def main():
    await aggregate_protocol_snapshot_data()


if __name__ == "__main__":
    asyncio.run(main())
