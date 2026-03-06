"""Qdrant vector database operations."""
from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.models import Distance, PayloadSchemaType, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)

# Singleton client — reuse connection across requests
_qdrant_client: QdrantClient | None = None


def _client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=settings.qdrant_url)
    return _qdrant_client


def ensure_collection() -> None:
    client = _client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embed_dim,
                distance=Distance.COSINE,
            ),
        )
        logger.info("[qdrant] Created collection '%s'", settings.qdrant_collection)


def ensure_tags_index() -> None:
    """Create a KEYWORD payload index on 'tags' for fast filtered search.

    Idempotent — safe to call on every startup.
    """
    client = _client()
    try:
        client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="tags",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("[qdrant] Keyword index on 'tags' created/verified")
    except Exception:
        # Already exists or collection doesn't exist yet — both are fine
        pass


def warmup() -> None:
    """Touch Qdrant to warm the HTTP connection pool and OS page cache."""
    client = _client()
    try:
        info = client.get_collection(settings.qdrant_collection)
        if info.points_count and info.points_count > 0:
            client.scroll(
                collection_name=settings.qdrant_collection,
                limit=1,
                with_payload=False,
                with_vectors=False,
            )
            logger.info("[qdrant] Warmup scroll completed")
        else:
            logger.info("[qdrant] Collection empty — skipping warmup scroll")
    except Exception as exc:
        logger.warning("[qdrant] Warmup skipped: %s", exc)


def search_by_tag(
    tag: str,
    top_n: int = 20,
    extra_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return assets whose 'tags' array contains *tag* (exact, keyword index).

    Uses scroll (no vector needed) — very fast with the KEYWORD index.
    Score is set to 1.0 to signal an exact tag match.
    """
    client = _client()
    conditions: list[Any] = [
        qmodels.FieldCondition(key="tags", match=qmodels.MatchValue(value=tag))
    ]
    if extra_filters:
        for k, v in extra_filters.items():
            if v is not None:
                conditions.append(
                    qmodels.FieldCondition(key=k, match=qmodels.MatchValue(value=v))
                )
    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=qmodels.Filter(must=conditions),
        limit=top_n,
        with_payload=True,
        with_vectors=False,
    )
    return [
        {"asset_id": str(p.id), "score": 1.0, "tag_match": True, **(p.payload or {})}
        for p in points
    ]


def upsert_asset(
    asset_id: str,
    embedding: list[float],
    payload: dict[str, Any],
) -> None:
    client = _client()
    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            qmodels.PointStruct(
                id=asset_id,
                vector=embedding,
                payload=payload,
            )
        ],
    )


def search(
    embedding: list[float],
    top_k: int = 10,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    client = _client()

    qdrant_filter = None
    if filters:
        conditions = []
        for key, value in filters.items():
            if value is not None:
                conditions.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchValue(value=value),
                    )
                )
        if conditions:
            qdrant_filter = qmodels.Filter(must=conditions)

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=embedding,
        limit=top_k,
        query_filter=qdrant_filter,
        with_payload=True,
    )

    return [
        {
            "asset_id": str(hit.id),
            "score": hit.score,
            **hit.payload,
        }
        for hit in results
    ]


def delete_by_filter(filter_payload: dict[str, Any]) -> None:
    client = _client()
    conditions = [
        qmodels.FieldCondition(key=k, match=qmodels.MatchValue(value=v))
        for k, v in filter_payload.items()
        if v is not None
    ]
    if not conditions:
        return
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(must=conditions)
        ),
    )


def get_asset(asset_id: str) -> dict[str, Any] | None:
    client = _client()
    results = client.retrieve(
        collection_name=settings.qdrant_collection,
        ids=[asset_id],
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        return None
    point = results[0]
    return {"asset_id": str(point.id), **(point.payload or {})}


def update_asset_tags(asset_id: str, tags: list[str]) -> None:
    client = _client()
    client.set_payload(
        collection_name=settings.qdrant_collection,
        payload={"tags": tags},
        points=[asset_id],
    )


def asset_exists_by_hash(content_hash: str) -> bool:
    client = _client()
    results = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="content_hash",
                    match=qmodels.MatchValue(value=content_hash),
                )
            ]
        ),
        limit=1,
    )
    return len(results[0]) > 0

def count_assets(filters: dict[str, Any] | None = None) -> int:
    client = _client()
    qdrant_filter = None
    conditions: list[Any] = []
    if filters:
        conditions = [
            qmodels.FieldCondition(key=k, match=qmodels.MatchValue(value=v))
            for k, v in filters.items()
            if v is not None
        ]
    if conditions:
        qdrant_filter = qmodels.Filter(must=conditions)

    res = client.count(
        collection_name=settings.qdrant_collection,
        count_filter=qdrant_filter,
        exact=True,
    )
    return int(res.count)