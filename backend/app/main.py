from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield


app = FastAPI(title="German Scene-Based SRS API", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "ok"}