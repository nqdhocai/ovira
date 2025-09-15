from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.user import UserOperations
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


@router.get("/balance/nav", response_model=float)
async def get_user_balance_nav(user_wallet: str, vault_name: str):
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
