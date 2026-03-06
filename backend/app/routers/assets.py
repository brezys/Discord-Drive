from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import vector_db

router = APIRouter(prefix="/assets", tags=["assets"])

DISCORD_JUMP_BASE = "https://discord.com/channels"


def _normalize_tag(raw: str) -> str:
    tag = raw.strip().lstrip("#")
    tag = re.sub(r"\s+", " ", tag).strip()
    return tag.lower()


def _normalize_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in tags:
        for part in raw.split(","):
            normalized = _normalize_tag(part)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
    return result


def _build_response(asset: dict) -> dict:
    asset_id = asset["asset_id"]
    guild_id = asset.get("guild_id", "")
    channel_id = asset.get("channel_id", "")
    message_id = asset.get("message_id", "")
    return {
        **asset,
        "thumb_url": f"/thumb/{asset_id}",
        "jump_url": f"{DISCORD_JUMP_BASE}/{guild_id}/{channel_id}/{message_id}",
        "tags": asset.get("tags", []),
    }


@router.get("/{asset_id}")
async def get_asset(asset_id: str):
    asset = vector_db.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _build_response(asset)


@router.get("/{asset_id}/tags")
async def get_asset_tags(asset_id: str):
    asset = vector_db.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"asset_id": asset_id, "tags": asset.get("tags", [])}


class TagsRequest(BaseModel):
    tags: list[str]


@router.put("/{asset_id}/tags")
async def put_asset_tags(asset_id: str, body: TagsRequest):
    asset = vector_db.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    normalized = _normalize_tags(body.tags)
    vector_db.update_asset_tags(asset_id, normalized)
    return {"asset_id": asset_id, "tags": normalized}
