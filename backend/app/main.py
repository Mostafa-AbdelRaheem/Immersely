import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.db import engine
from app.core.limiter import limiter
from app.services.embeddings import warm_up_model
from app.api.auth import router as auth_router
from app.api.sentences import router as sentences_router
from app.api.topics import router as topics_router
from app.api.scenes import router as scenes_router
from app.api.review import router as review_router
from app.api.stats import router as stats_router
from app.api.articles import router as articles_router
from app.api.conversations import router as conversations_router
from app.api.sentence_import import router as sentence_import_router
from app.api import srs
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    # Load the embedding model in the background so the first save is fast.
    # The task is held in a local so it cannot be garbage-collected mid-run.
    warm_up_task = asyncio.create_task(warm_up_model())
    try:
        yield
    finally:
        warm_up_task.cancel()
        try:
            await warm_up_task
        except asyncio.CancelledError:
            pass


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
app.include_router(topics_router)
app.include_router(srs.router)
app.include_router(scenes_router)
app.include_router(review_router)
app.include_router(stats_router)
app.include_router(articles_router)
app.include_router(conversations_router)
app.include_router(sentence_import_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}