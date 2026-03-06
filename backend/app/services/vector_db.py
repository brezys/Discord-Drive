"""Qdrant vector database operations."""
from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.models import Distance, VectorParams

from app.config import settings


def _client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


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
