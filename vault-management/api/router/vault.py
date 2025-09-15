from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException

from backend.vault import VaultOperations, VaultStrategyUpdatedInfo
from hooks.error import ResourceNotFound
from hooks.success import SuccessResponse
from mongo.schemas import PoolAllocation, ReasoningTrace

router = APIRouter(prefix="/vault", tags=["vault"])


@router.post("/create_vault", response_model=SuccessResponse)
async def create_vault(
    vault_name: str,
    owner_wallet_address: str,
    asset: Literal["USDT", "USDC"],
    risk_label: Literal["conservative", "balanced", "aggressive"],
    update_frequency: float = 6.0,
    policy_prompt: str | None = None,
):
    r"""
    Create a new vault.

    - Query/body params: `vault_name` (str), `owner_wallet_address` (str), `asset` (str), `risk_label` (str).
    - Optional: `update_frequency` (float, hours, default 6.0), `policy_prompt` (str | None).
    - Success: returns `SuccessResponse` (200) when vault is created.
    - Errors: 500 on failure.
    """
    try:
        await VaultOperations.create_vault(
            vault_name,
            owner_wallet_address,
            asset,
            risk_label,
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
    r"""
    Update a vault's policy parameters.

    - Query params: `vault_name` (str), optional `new_update_frequency` (float), `new_policy_prompt` (str).
    - Success: returns `SuccessResponse` (200) when updated.
    - Errors: 404 if vault not found, 500 on other failures.
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
    r"""
    Retrieve the latest APY for a vault.

    - Query params: `vault_name` (str).
    - Success: returns a float - the latest APY for the vault.
    - Errors: 404 if vault not found, 500 on other failures.
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
    r"""
    Retrieve the latest TVL for a vault.

    - Query params: `vault_name` (str).
    - Success: returns a float - the latest TVL for the vault.
    - Errors: 404 if no snapshot found, 500 on other failures.
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
    r"""
    Retrieve the APY time series for a vault.

    - Query params: `vault_name` (str), optional `days` (int, default 30).
    - Success: returns a list of (datetime, float) tuples for APY over time.
    - Errors: 404 if no data found, 500 on other failures.
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
    r"""
    Retrieve the TVL time series for a vault.

    - Query params: `vault_name` (str), optional `days` (int, default 30).
    - Success: returns a list of (datetime, float) tuples for TVL over time.
    - Errors: 404 if no data found, 500 on other failures.
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
    r"""
    Retrieve allocation details for a vault.

    - Query params: `vault_name` (str).
    - Success: returns a list of `PoolAllocation` models (pool_name: str, weight_pct: float).
    - Errors: 404 if no allocation data found, 500 on other failures.
    """
    try:
        return await VaultOperations.get_vault_allocations(vault_name)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get vault allocations: {str(e)}"
        )


@router.get("/recent_action", response_model=list[VaultStrategyUpdatedInfo])
async def get_strategy_updated_history(vault_name: str, days: int = 3):
    r"""
    Retrieve the vault's strategy update history.

    - Query params: `vault_name` (str), optional `days` (int, default 30).
    - Success: returns a list of `VaultStrategyUpdatedInfo` entries (timestamp: datetime, action: str, details: str).
    - Errors: 404 if no history found, 500 on other failures.
    """
    try:
        return await VaultOperations.get_strategy_updated_history(vault_name, days)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get strategy updated history: {str(e)}"
        )


@router.get("/ai_reasoning_trace", response_model=list[ReasoningTrace])
async def get_vault_reasoning_trace(vault_name: str):
    r"""
    Retrieve the vault's strategy reasoning trace.

    - Query params: `vault_name` (str)
    - Success: returns a list of `ReasoningTrace` entries (role: str, content: str).
    - Errors: 404 if no history found, 500 on other failures.
    """
    try:
        return await VaultOperations.get_strategy_ai_reasoning_trace(
            vault_name=vault_name
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get strategy AI reasoning trace: {str(e)}",
        )


@router.get("/existing_vaults", response_model=list[str])
async def get_existing_vaults():
    r"""
    Get list of existing vault. Return list[str] is list of vaults's name
    """
    return await VaultOperations.get_existing_vaults()
