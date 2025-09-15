from typing import Any

from fastapi import APIRouter, HTTPException

from backend.strategy import StrategyOperations
from hooks.error import ResourceNotFound
from hooks.success import SuccessResponse
from mongo.schemas import StrategyInfo

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/update_vault_strategy", response_model=SuccessResponse)
async def update_vault_strategy(strategy: dict[str, Any], vault_name: str):
    r"""Update vault strategy.

    Inputs:
        strategy (dict): Representing the vault strategy.
        vault_name (str): The name of the vault to update.

    Outputs:
        On success, returns a `SuccessResponse` Pydantic model with status and
        message. On failure, raises an HTTPException with status 500 and an
        error message describing the failure.
    """
    try:
        strategy_ops = StrategyOperations(
            StrategyInfo.model_validate(strategy), vault_name
        )
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
