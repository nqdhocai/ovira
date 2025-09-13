from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.transaction import TransactionOperations
from hooks.error import ResourceNotFound
from hooks.success import SuccessResponse

router = APIRouter(prefix="/transaction", tags=["transaction"])


@router.post("/deposit", response_model=SuccessResponse)
async def deposit(vault_name: str, amount: float, user_wallet: str):
    r"""Deposit funds into a vault.

    Inputs:
        vault_name (str): The name of the vault to deposit into.
        amount (float): The amount to deposit.
        user_wallet (str): The wallet address of the user making the deposit.

    Outputs:
        On success, returns a `SuccessResponse` Pydantic model with status and
        message. On failure, raises an HTTPException with status 500 and an
        error message describing the failure.
    """
    try:
        await TransactionOperations.deposit(vault_name, amount, user_wallet)
        return SuccessResponse(status_code=200, message="Deposit successful.")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deposit failed: {str(e)}")


@router.post("/withdraw", response_model=SuccessResponse)
async def withdraw(vault_name: str, amount: float, user_wallet: str):
    r"""Withdraw funds from a vault.

    Inputs:
        vault_name (str): The name of the vault to withdraw from.
        amount (float): The amount to withdraw.
        user_wallet (str): The wallet address of the user making the withdrawal.

    Outputs:
        On success, returns a `SuccessResponse` Pydantic model with status and
        message. On failure, raises an HTTPException with status 500 and an
        error message describing the failure.
    """
    try:
        await TransactionOperations.withdraw(vault_name, amount, user_wallet)
        return SuccessResponse(status_code=200, message="Withdrawal successful.")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Withdrawal failed: {str(e)}")
