from fastapi import APIRouter, HTTPException

from backend.transaction import TransactionOperations
from hooks.error import ResourceNotFound
from hooks.success import SuccessResponse

router = APIRouter(prefix="/transaction", tags=["transaction"])


@router.post("/deposit", response_model=SuccessResponse)
async def deposit(vault_name: str, amount: float, user_wallet: str):
    r"""
    Deposit funds into a vault.

    - Query params: `vault_name` (str), `amount` (float), `user_wallet` (str).
    - Success: returns `SuccessResponse` with a confirmation message (200).
    - Errors: 404 if referenced resources are missing, 500 on other failures.
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
    r"""
    Withdraw funds from a vault.

    - Query params: `vault_name` (str), `amount` (float), `user_wallet` (str).
    - Success: returns `SuccessResponse` confirming the withdrawal (200).
    - Errors: 404 if resources are missing, 500 on other failures.
    """
    try:
        await TransactionOperations.withdraw(vault_name, amount, user_wallet)
        return SuccessResponse(status_code=200, message="Withdrawal successful.")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Withdrawal failed: {str(e)}")
