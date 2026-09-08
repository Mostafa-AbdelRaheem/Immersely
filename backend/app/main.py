from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.db import engine
from app.core.limiter import limiter
from app.api.auth import router as auth_router
from app.api.sentences import router as sentences_router
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield


app = FastAPI(title="German Scene-Based SRS API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth_router)
app.include_router(sentences_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}