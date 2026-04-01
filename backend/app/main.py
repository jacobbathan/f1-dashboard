from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from backend.app.api.routes_races import router as races_router
import backend.app.db.tables  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.engine import engine
from backend.app.services.ingestion import enable_cache


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup tasks before the app begins serving requests."""
    Base.metadata.create_all(bind=engine)
    enable_cache()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(races_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok"}
