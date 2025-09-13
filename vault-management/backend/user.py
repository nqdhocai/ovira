from configs import get_logger
from hooks.error import ResourceNotFound
from mongo.schemas import UserMetadata
from utils import hasher

logger = get_logger("user_operations")


class UserOperations:
    @staticmethod
    async def create_user(wallet_address: str) -> UserMetadata:
        existing_user = await UserMetadata.find_one(
            UserMetadata.wallet_address == wallet_address
        )
        if existing_user:
            raise ResourceNotFound(f"User with wallet {wallet_address} already exists.")
        else:
            new_user = UserMetadata(
                id=hasher.get_hash(wallet_address), wallet_address=wallet_address
            )
            _ = await new_user.save()
            logger.info(f"User with wallet {wallet_address} created successfully.")
            return new_user
