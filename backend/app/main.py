import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware import verify_api_key
from app.routers import admin, assets, ingest, query, thumbnails
from app.services import embedder, vector_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[startup] Ensuring Qdrant collection and indexes…")
    vector_db.ensure_collection()
    vector_db.ensure_tags_index()

    logger.info("[startup] Warming up embedding model…")
    embedder.warmup()          # loads model + one dummy inference

    logger.info("[startup] Warming up Qdrant connection…")
    vector_db.warmup()         # touches collection to warm HTTP pool

    logger.info("[startup] Ready")
    yield


app = FastAPI(
    title="Latent Assets API",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(thumbnails.router)
app.include_router(admin.router)
app.include_router(assets.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
