from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from clients import Clients

from .router import strategy, transaction, user, vault

mongo_client = Clients.get_mongo_client()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo_client.initialize()
    yield
    await mongo_client.close()


app = FastAPI(
    title="Vault Management API",
    description="API for managing and interacting with vaults.",
    lifespan=lifespan,
)

app.include_router(vault.router)
app.include_router(user.router)
app.include_router(transaction.router)
app.include_router(strategy.router)

if __name__ == "__main__":
    uvicorn.run("api.api_main:app", host="0.0.0.0", port=8000)
