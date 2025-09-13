from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.user import UserOperations
from hooks.error import ResourceNotFound
from hooks.success import SuccessResponse

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/create_user", response_model=SuccessResponse)
async def create_user(user_wallet: str):
    r"""Create a new user.

    Inputs:
        user_wallet (str): The wallet address of the user to create.

    Outputs:
        On success, returns a `SuccessResponse` Pydantic model with status and
        message. On failure, raises an HTTPException with status 500 and an
        error message describing the failure.
    """
    try:
        _ = await UserOperations.create_user(user_wallet)
        return SuccessResponse(status_code=200, message="User created successfully.")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.get("/balance", response_model=float)
async def get_user_balance(user_wallet: str, vault_name: str):
    r"""Get the balance of a user in a specific vault.

    Inputs:
        user_wallet (str): The wallet address of the user.
        vault_name (str): The name of the vault.

    Outputs:
        On success, returns the balance of the user in the specified vault.
        On failure, raises an HTTPException with status 404 and an error message
        describing the failure.
    """
    try:
        balance = await UserOperations.get_user_balance(user_wallet, vault_name)
        return balance
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get user balance: {str(e)}"
        )
