from datetime import datetime

from clients import Clients
from configs import get_logger
from mongo.schemas import (
    DeFiLlamaData,
    DerivedData,
    ProtocolsMetadata,
    ProtocolSnapshot,
)
from utils import hasher
from utils.timestamp import floor_to_hour

from .defillama_data import aggregate_defillama_data
from .derived_data import compute_derived_data

logger = get_logger("aggregate_data")
mongo_client = Clients.get_mongo_client()


async def aggregate_protocol_snapshot_data():
    # await mongo_client.initialize()
    ts = floor_to_hour(int(datetime.utcnow().timestamp()))

    protocols_docs = await ProtocolsMetadata.find_all().to_list()
    for protocol in protocols_docs:
        defillama_data = await aggregate_defillama_data(
            protocol_id=protocol.defillamaId, timestamp=ts
        )
        derived_data = await compute_derived_data(
            defillama_data=defillama_data, ts_now=ts, protocol_id=protocol.defillamaId
        )
        protocol_snapshot: ProtocolSnapshot = ProtocolSnapshot(
            id=hasher.get_hash(f"{protocol.defillamaId}:{ts}"),
            protocol=protocol.slug,
            chain="solana",
            category=protocol.category,
            timestamp=ts,
            defillama=defillama_data,
            derived=derived_data,
        )
        _ = await protocol_snapshot.save()
