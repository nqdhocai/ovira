from typing import Any

from fastapi import APIRouter, HTTPException

from backend.strategy import StrategyOperations
from hooks.error import ResourceNotFound
from hooks.success import SuccessResponse
from mongo.schemas import StrategyInfo

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/update_vault_strategy", response_model=SuccessResponse)
async def update_vault_strategy(strategy: StrategyInfo, vault_name: str):
    r"""
    Update a vault's strategy.

    - Request body: `strategy` (mongo.schemas.StrategyInfo) — the new strategy payload.
    - Query/path: `vault_name` (str) — vault identifier to update.

    Responses:
    - 200: `SuccessResponse` when the strategy is updated successfully.
    - 404: when the referenced resource is not found.
    - 500: on unexpected server errors.
    """
    try:
        strategy_ops = StrategyOperations(strategy, vault_name)
        await strategy_ops.upload_vault_data()
        return SuccessResponse(
            status_code=200, message="Vault strategy updated successfully."
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update vault strategy: {str(e)}"
        )
