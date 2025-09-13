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
