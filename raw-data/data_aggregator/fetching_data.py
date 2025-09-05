import asyncio

from pymongo.errors import DuplicateKeyError

from clients import Clients
from configs import get_logger
from mongo.schemas import (
    ChainVolume,
    DexsOverview,
    ProtocolsFee,
    ProtocolsMetadata,
    ProtocolsTVL,
    StableCoinsData,
)
from utils import hasher

from .defillama_operators.dexs_overview import get_chain_volume_24h, get_dexs_overview
from .defillama_operators.fee import get_protocols_fee
from .defillama_operators.protocols import get_protocols_metadata
from .defillama_operators.stablecoins import get_stablecoins_data
from .defillama_operators.tvl import get_protocols_tvl

logger = get_logger("defillama_data")

mongo_client = Clients.get_mongo_client()


async def fetch_and_store_defillama_data():
    await mongo_client.initialize()
    protocols = await get_protocols_metadata()
    if protocols:
        for protocol in protocols:
            # Store protocol metadata
            protocol_metadata = ProtocolsMetadata(
                id=hasher.get_hash(f"{protocol.defillamaId}"),
                defillamaId=protocol.defillamaId,
                url=protocol.url,
                name=protocol.name,
                symbol=protocol.symbol,
                description=protocol.description,
                category=protocol.category,
                slug=protocol.slug,
            )
            try:
                _ = await protocol_metadata.save()
            except DuplicateKeyError:
                logger.info(
                    f"Protocol metadata with defillamaId {protocol.defillamaId} already exists. Skipping insertion."
                )

            # Fetch and store TVL data
            protocol_tvl = await get_protocols_tvl(protocol_slug=protocol.slug)
            if protocol_tvl:
                protocol_tvl_entry: ProtocolsTVL = ProtocolsTVL(
                    id=hasher.get_hash(
                        f"{protocol.defillamaId}:{str(protocol_tvl.timestamp)}"
                    ),
                    protocol=protocol_metadata,
                    timestamp=protocol_tvl.timestamp,
                    tvl_change_24h=protocol_tvl.tvl_change_24h,
                    tvl_change_7d=protocol_tvl.tvl_change_7d,
                    tvl_change_30d=protocol_tvl.tvl_change_30d,
                    tvl_usd=protocol_tvl.tvl_usd,
                    tvl_history_30d=protocol_tvl.tvl_history_30d,
                )
                try:
                    _ = await protocol_tvl_entry.save()
                except DuplicateKeyError:
                    logger.info(
                        f"Protocol TVL with defillamaId {protocol.defillamaId} at timestamp {protocol_tvl.timestamp} already exists. Skipping insertion."
                    )

            # Fetch and store Fee data
            protocol_fee = await get_protocols_fee(
                protocol_slug=protocol.slug, protocol_id=protocol.defillamaId
            )
            if protocol_fee:
                protocol_fee_entry = ProtocolsFee(
                    id=hasher.get_hash(
                        f"{protocol.defillamaId}:{str(protocol_fee.timestamp)}"
                    ),
                    protocol=protocol_metadata,
                    defillamaId=protocol_fee.defillamaId,
                    timestamp=protocol_fee.timestamp,
                    total24h=protocol_fee.total24h,
                    total7d=protocol_fee.total7d,
                    total30d=protocol_fee.total30d,
                )
                try:
                    _ = await protocol_fee_entry.save()
                except DuplicateKeyError:
                    logger.info(
                        f"Protocol Fee with defillamaId {protocol.defillamaId} at timestamp {protocol_fee.timestamp} already exists. Skipping insertion."
                    )

        protocols_dexs_overview = await get_dexs_overview(
            protocolsID=[protocol.defillamaId for protocol in protocols]
        )
        if protocols_dexs_overview:
            for dexs_overview in protocols_dexs_overview:
                protocol = await ProtocolsMetadata.find_one(
                    ProtocolsMetadata.defillamaId == dexs_overview.defillamaId
                )
                if protocol:
                    dexs_overview_entry = DexsOverview(
                        id=hasher.get_hash(
                            f"{str(dexs_overview.defillamaId)}:{str(dexs_overview.timestamp)}"
                        ),
                        protocol=protocol,
                        defillamaId=dexs_overview.defillamaId,
                        timestamp=dexs_overview.timestamp,
                        total24hVolume=dexs_overview.total24hVolume,
                        total7dVolume=dexs_overview.total7dVolume,
                        total30dVolume=dexs_overview.total30dVolume,
                        totalAllTimeVolume=dexs_overview.totalAllTimeVolume,
                    )
                    try:
                        _ = await dexs_overview_entry.save()
                    except DuplicateKeyError:
                        logger.info(
                            f"Dexs Overview with defillamaId {dexs_overview.defillamaId} at timestamp {dexs_overview.timestamp} already exists. Skipping insertion."
                        )
    stablecoins_data = await get_stablecoins_data()
    if stablecoins_data:
        stablecoins_data_entry = StableCoinsData(
            id=hasher.get_hash(f"{str(stablecoins_data.timestamp)}"),
            timestamp=stablecoins_data.timestamp,
            totalCirculating=stablecoins_data.totalCirculating,
            totalCirculatingUSD=stablecoins_data.totalCirculatingUSD,
            off_peg_pct=stablecoins_data.off_peg_pct,
        )
        try:
            _ = await stablecoins_data_entry.save()
        except DuplicateKeyError:
            logger.info(
                f"StableCoins Data with timestamp {stablecoins_data.timestamp} already exists. Skipping insertion."
            )

    chain_volume_24h = await get_chain_volume_24h()
    if chain_volume_24h:
        chain_volume_entry = ChainVolume(
            id=hasher.get_hash(f"{chain_volume_24h.timestamp}"),
            timestamp=chain_volume_24h.timestamp,
            volume_24h_usd=chain_volume_24h.total24h,
        )
        try:
            _ = await chain_volume_entry.save()
        except DuplicateKeyError:
            logger.info(
                f"Chain Volume Data with timestamp {chain_volume_entry.timestamp} already exists. Skipping insertion."
            )


if __name__ == "__main__":
    asyncio.run(fetch_and_store_defillama_data())
