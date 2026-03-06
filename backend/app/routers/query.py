from __future__ import annotations

import logging
import re
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import embedder, vector_db

router = APIRouter(tags=["query"])
logger = logging.getLogger(__name__)

DISCORD_JUMP_BASE = "https://discord.com/channels"

# Matches "tag:cat", "#cat", "tag: cat with spaces" — capture group 1 is the raw tag
_EXPLICIT_TAG_RE = re.compile(r"^(?:tag:|#)(.+)$", re.IGNORECASE)

# A single "word-like" token that could be an exact tag
_SIMPLE_TOKEN_RE = re.compile(r"^[a-z0-9_\-]{1,64}$")

# How many tag-matched assets to fetch before merging with semantic results
_TAG_FETCH_LIMIT = 20


def _extract_tag_query(query_text: str) -> tuple[str, str | None]:
    """Return (cleaned_query_for_embedding, tag_to_lookup | None).

    - "tag:cat" or "#cat"  → ("cat", "cat")      explicit forced mode
    - "cat"                → ("cat", "cat")      simple token, try tag lookup too
    - "thinking hard"      → ("thinking hard", None)  multi-word, semantic only
    """
    stripped = query_text.strip()
    m = _EXPLICIT_TAG_RE.match(stripped)
    if m:
        tag = m.group(1).strip().lower()
        return tag, tag

    normalized = stripped.lower()
    if _SIMPLE_TOKEN_RE.match(normalized):
        return stripped, normalized

    return stripped, None


# ── Request / Response models ─────────────────────────────────────────────────

class QueryFilters(BaseModel):
    guild_id: str | None = None
    channel_id: str | None = None
    author_id: str | None = None


class QueryRequest(BaseModel):
    query_text: str
    top_k: int | None = Field(default=10, ge=1, le=100)
    filters: QueryFilters = Field(default_factory=QueryFilters)


class AssetResult(BaseModel):
    asset_id: str
    score: float
    thumb_url: str
    jump_url: str
    tags: list[str]
    tag_match: bool
    metadata: dict[str, Any]


class QueryResponse(BaseModel):
    results: list[AssetResult]
    total_available: int


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query_images(req: QueryRequest):
    t0 = time.perf_counter()

    embed_query, tag_query = _extract_tag_query(req.query_text)

    # Build extra payload filters (guild/channel/author)
    active_filters: dict[str, Any] = {}
    if req.filters.guild_id:
        active_filters["guild_id"] = req.filters.guild_id
    if req.filters.channel_id:
        active_filters["channel_id"] = req.filters.channel_id
    if req.filters.author_id:
        active_filters["author_id"] = req.filters.author_id

    total_available = vector_db.count_assets(active_filters or None)
    if total_available == 0:
        return QueryResponse(results=[], total_available=0)

    effective_top_k = total_available if req.top_k is None else min(req.top_k, total_available)

    # ── Stage 1: tag-filtered retrieval ──────────────────────────────────────
    tag_hits: list[dict[str, Any]] = []
    if tag_query:
        t_tag0 = time.perf_counter()
        tag_hits = vector_db.search_by_tag(
            tag_query,
            top_n=_TAG_FETCH_LIMIT,
            extra_filters=active_filters or None,
        )
        logger.info(
            "[query] tag='%s' → %d hits in %.1fms",
            tag_query,
            len(tag_hits),
            (time.perf_counter() - t_tag0) * 1000,
        )

    # ── Stage 2: semantic vector retrieval ───────────────────────────────────
    t_emb0 = time.perf_counter()
    text_embedding = embedder.embed_text(embed_query)
    logger.info("[query] embed in %.1fms", (time.perf_counter() - t_emb0) * 1000)

    t_search0 = time.perf_counter()
    semantic_hits = vector_db.search(
        text_embedding,
        top_k=effective_top_k,
        filters=active_filters or None,
    )
    logger.info(
        "[query] semantic → %d hits in %.1fms",
        len(semantic_hits),
        (time.perf_counter() - t_search0) * 1000,
    )

    # ── Stage 3: merge — tag hits first, then semantic (deduplicated) ────────
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []

    for hit in tag_hits:
        aid = hit["asset_id"]
        if aid not in seen:
            seen.add(aid)
            hit.setdefault("tag_match", True)
            merged.append(hit)

    for hit in semantic_hits:
        aid = hit["asset_id"]
        if aid not in seen:
            seen.add(aid)
            hit.setdefault("tag_match", False)
            merged.append(hit)

    merged = merged[:effective_top_k]

    logger.info(
        "[query] total=%.1fms results=%d (tag=%d semantic=%d)",
        (time.perf_counter() - t0) * 1000,
        len(merged),
        sum(1 for h in merged if h.get("tag_match")),
        sum(1 for h in merged if not h.get("tag_match")),
    )

    # ── Build response ────────────────────────────────────────────────────────
    results = []
    for hit in merged:
        asset_id = hit["asset_id"]
        guild_id = hit.get("guild_id", "")
        channel_id = hit.get("channel_id", "")
        message_id = hit.get("message_id", "")

        results.append(
            AssetResult(
                asset_id=asset_id,
                score=hit["score"],
                thumb_url=f"/thumb/{asset_id}",
                jump_url=f"{DISCORD_JUMP_BASE}/{guild_id}/{channel_id}/{message_id}",
                tags=hit.get("tags", []),
                tag_match=hit.get("tag_match", False),
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

    return QueryResponse(results=results, total_available=total_available)
