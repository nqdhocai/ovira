from fastapi import APIRouter, HTTPException

from backend.user import UserOperations, VaultData
from hooks.error import ResourceNotFound
from hooks.success import SuccessResponse

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/create_user", response_model=SuccessResponse)
async def create_user(user_wallet: str):
    r"""
    Create a new user record.

    - Query/body: `user_wallet` (str) — wallet address to register.
    - Success: returns `SuccessResponse` (200) on successful creation.
    - Errors: 404 if related resources are missing, 500 on server errors.
    """
    try:
        _ = await UserOperations.create_user(user_wallet)
        return SuccessResponse(status_code=200, message="User created successfully.")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.get("/balance/net_value", response_model=float)
async def get_user_balance_net_value(user_wallet: str, vault_name: str):
    r"""
    Get a user's balance NAV (Net Asset Value) for a given vault.

    - Query params: `user_wallet` (str), `vault_name` (str).
    - Success: returns a float representing the user's balance NAV in the vault.
    - Errors: 404 if the user or vault is not found, 500 on other failures.
    """
    try:
        balance = await UserOperations.get_user_balance_nav(user_wallet, vault_name)
        return balance
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get user balance: {str(e)}"
        )


@router.get("/balance/earnings", response_model=float)
async def get_user_balance_earnings(user_wallet: str, vault_name: str):
    r"""
    Get a user's balance earnings for a given vault.

    - Query params: `user_wallet` (str), `vault_name` (str).
    - Success: returns a float representing the user's balance earnings in the vault.
    - Errors: 404 if the user or vault is not found, 500 on other failures.
    """
    try:
        balance = await UserOperations.get_user_balance_earnings(
            user_wallet, vault_name
        )
        return balance
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get user balance: {str(e)}"
        )


@router.post("/balance/update_earnings", response_model=SuccessResponse)
async def update_user_balance_earnings(
    user_wallet: str, vault_name: str, time_interval: float = 6.0
):
    r"""
    Update a user's balance earnings for a given vault over a specified time interval.

    - Query/body: `user_wallet` (str), `vault_name` (str), `time_interval` (float) in hours.
    - Success: returns `SuccessResponse` (200) when earnings are updated successfully.
    - Errors: 404 if the user or vault is not found, 500 on other failures.
    """
    try:
        await UserOperations.update_user_balance_earnings(
            user_wallet, vault_name, time_interval
        )
        return SuccessResponse(
            status_code=200, message="User earnings updated successfully."
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update user earnings: {str(e)}"
        )


@router.get("/personal_vaults", response_model=dict[int, VaultData])
async def get_all_personal_vaults_for_a_user(user_wallet: str):
    """
    Get all personal vault for a user wallet with additional information.

    Args:
        `user_wallet (str)`: user wallet address

    Returns:
        `dict[int, VaultData]`: information about each vault that the user is having, ranked by tvl from highest to lower
    """
    try:
        return await UserOperations.get_all_vaults(user_wallet)
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error when trying to get personal vault: {e}",
        )
