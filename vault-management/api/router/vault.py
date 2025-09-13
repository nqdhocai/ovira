from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.vault import VaultOperations, VaultStrategyUpdatedInfo
from hooks.error import ResourceNotFound
from hooks.success import SuccessResponse
from mongo.schemas import PoolAllocation

router = APIRouter(prefix="/vault", tags=["vault"])


@router.post("/create_vault", response_model=SuccessResponse)
async def create_vault(
    vault_name: str,
    owner_wallet_address: str,
    asset: str,
    update_frequency: float = 6.0,
    policy_prompt: str | None = None,
):
    r"""Create a new vault.

    Inputs:
        vault_name (str): The name of the vault to create.
        owner_wallet_address (str): The wallet address of the vault owner.
        asset (str): The asset associated with the vault. (e.g., 'USDT', 'USDC')
        update_frequency (float, optional): Frequency in hours for updating the vault. Defaults to 6.0.
        policy_prompt (str | None, optional): Optional policy prompt for the vault. Defaults to None.

    Outputs:
        On success, returns a `SuccessResponse` Pydantic model with status and
        message. On failure, raises an HTTPException with status 500 and an
        error message describing the failure.
    """
    try:
        await VaultOperations.create_vault(
            vault_name,
            owner_wallet_address,
            asset,
            update_frequency,
            policy_prompt,
        )
        return SuccessResponse(status_code=200, message="Vault created successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create vault: {str(e)}")


@router.post("/update_vault_policy", response_model=SuccessResponse)
async def update_vault_policy(
    vault_name: str,
    new_update_frequency: float | None = None,
    new_policy_prompt: str | None = None,
):
    r"""Update vault policy.

    Inputs:
        vault_name (str): The name of the vault to update.
        new_update_frequency (float | None, optional): New frequency in hours for updating the vault. Defaults to None.
        new_policy_prompt (str | None, optional): New policy prompt for the vault. Defaults to None.

    Outputs:
        On success, returns a `SuccessResponse` Pydantic model with status and
        message. On failure, raises an HTTPException with status 500 and an
        error message describing the failure.
    """
    try:
        await VaultOperations.update_vault_policy(
            vault_name,
            new_update_frequency,
            new_policy_prompt,
        )
        return SuccessResponse(
            status_code=200, message="Vault policy updated successfully."
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update vault policy: {str(e)}"
        )


@router.get("/apy", response_model=float)
async def get_vault_apy(vault_name: str):
    r"""Retrieve the latest APY for a vault.
    Inputs:
        vault_name (str): The name of the vault to query.
    Outputs:
        float: The latest vault APY value. If no vault is found, raises
        HTTPException(404).
    """
    try:
        return await VaultOperations.get_vault_apy(vault_name)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get vault APY: {str(e)}"
        )


@router.get("/tvl", response_model=float)
async def get_vault_tvl(vault_name: str):
    r"""Retrieve the latest TVL for a vault.
    Inputs:
        vault_name (str): The name of the vault to query.
    Outputs:
        float: The latest vault TVL value. If no snapshot is found, raises
        HTTPException(404).
    """
    try:
        return await VaultOperations.get_vault_tvl(vault_name)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get vault TVL: {str(e)}"
        )


@router.get("/apy_chart", response_model=list[tuple[datetime, float]])
async def get_apy_chart(vault_name: str, days: int = 30):
    r"""Retrieve the APY chart for a vault.
    Inputs:
        vault_name (str): The name of the vault to query.
        days (int, optional): The number of days to look back for the chart. Defaults to 30.
    Outputs:
        list[tuple[datetime, float]]: A list of tuples containing the timestamp and APY value.
        If no data is found, raises HTTPException(404).
    """
    try:
        return await VaultOperations.get_apy_chart(vault_name, days)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get APY chart: {str(e)}"
        )


@router.get("/tvl_chart", response_model=list[tuple[datetime, float]])
async def get_tvl_chart(vault_name: str, days: int = 30):
    r"""Retrieve the TVL chart for a vault.
    Inputs:
        vault_name (str): The name of the vault to query.
        days (int, optional): The number of days to look back for the chart. Defaults to 30.
    Outputs:
        list[tuple[datetime, float]]: A list of tuples containing the timestamp and TVL value.
        If no data is found, raises HTTPException(404).
    """
    try:
        return await VaultOperations.get_tvl_chart(vault_name, days)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get TVL chart: {str(e)}"
        )


@router.get("/allocations", response_model=list[PoolAllocation])
async def get_vault_allocations(vault_name: str):
    r"""Retrieve the allocation details for a vault.
    Inputs:
        vault_name (str): The name of the vault to query.
    Outputs:
        list[PoolAllocation]: A list of pool allocation details for the vault.
            PoolAllocation:
                - pool_name (str): The name of the pool.
                - weight (float): The weight of the pool in the vault's strategy.
        If no data is found, raises HTTPException(404).
    """
    try:
        return await VaultOperations.get_vault_allocations(vault_name)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get vault allocations: {str(e)}"
        )


@router.get("/strategy_updated_history", response_model=list[VaultStrategyUpdatedInfo])
async def get_strategy_updated_history(vault_name: str, days: int = 30):
    r"""Retrieve the strategy updated history for a vault.
    Inputs:
        vault_name (str): The name of the vault to query.
        days (int, optional): The number of days to look back for the history. Defaults to 30.
    Outputs:
        list[VaultStrategyUpdatedInfo]: A list of strategy update details for the vault.
            VaultStrategyUpdatedInfo:
                - timestamp (datetime): The timestamp of the update.
                - action (str): The action taken (e.g., "created", "updated").
                - details (str): Additional details about the update.
        If no data is found, raises HTTPException(404).
    """
    try:
        return await VaultOperations.get_strategy_updated_history(vault_name, days)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get strategy updated history: {str(e)}"
        )
