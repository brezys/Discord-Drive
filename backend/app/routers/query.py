from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import embedder, vector_db

router = APIRouter(tags=["query"])

DISCORD_JUMP_BASE = "https://discord.com/channels"


class QueryFilters(BaseModel):
    guild_id: str | None = None
    channel_id: str | None = None
    author_id: str | None = None


class QueryRequest(BaseModel):
    query_text: str
    top_k: int = Field(default=10, ge=1, le=50)
    filters: QueryFilters = Field(default_factory=QueryFilters)


class AssetResult(BaseModel):
    asset_id: str
    score: float
    thumb_url: str
    jump_url: str
    metadata: dict[str, Any]


class QueryResponse(BaseModel):
    results: list[AssetResult]


@router.post("/query", response_model=QueryResponse)
async def query_images(req: QueryRequest):
    text_embedding = embedder.embed_text(req.query_text)

    active_filters: dict[str, Any] = {}
    if req.filters.guild_id:
        active_filters["guild_id"] = req.filters.guild_id
    if req.filters.channel_id:
        active_filters["channel_id"] = req.filters.channel_id
    if req.filters.author_id:
        active_filters["author_id"] = req.filters.author_id

    hits = vector_db.search(text_embedding, top_k=req.top_k, filters=active_filters or None)

    results = []
    for hit in hits:
        asset_id = hit["asset_id"]
        guild_id = hit.get("guild_id", "")
        channel_id = hit.get("channel_id", "")
        message_id = hit.get("message_id", "")

        jump_url = f"{DISCORD_JUMP_BASE}/{guild_id}/{channel_id}/{message_id}"
        thumb_url = f"/thumb/{asset_id}"

        results.append(
            AssetResult(
                asset_id=asset_id,
                score=hit["score"],
                thumb_url=thumb_url,
                jump_url=jump_url,
                metadata={
                    "channel_id": channel_id,
                    "author_id": hit.get("author_id", ""),
                    "created_at": hit.get("created_at", ""),
                    "filename": hit.get("attachment_filename", ""),
                    "mime_type": hit.get("mime_type", ""),
                    "width": hit.get("width", 0),
                    "height": hit.get("height", 0),
                },
            )
        )

    return QueryResponse(results=results)
