from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import channel_registry, vector_db

router = APIRouter(prefix="/admin", tags=["admin"])


class ChannelConfig(BaseModel):
    guild_id: str
    channel_id: str
    enabled: bool
    admin_id: str = ""


class DeleteRequest(BaseModel):
    guild_id: str
    channel_id: str | None = None
    message_id: str | None = None


@router.post("/channel")
async def set_channel_indexing(body: ChannelConfig):
    channel_registry.set_channel(body.guild_id, body.channel_id, body.enabled, body.admin_id)
    return {"status": "ok"}


@router.get("/channel/{guild_id}/{channel_id}")
async def get_channel_status(guild_id: str, channel_id: str):
    enabled = channel_registry.is_enabled(guild_id, channel_id)
    return {"guild_id": guild_id, "channel_id": channel_id, "enabled": enabled}


@router.get("/channels")
async def list_channels():
    return {"channels": channel_registry.get_all()}


@router.delete("/assets")
async def delete_assets(body: DeleteRequest):
    if body.channel_id:
        vector_db.delete_by_filter({"guild_id": body.guild_id, "channel_id": body.channel_id})
    elif body.message_id:
        vector_db.delete_by_filter({"guild_id": body.guild_id, "message_id": body.message_id})
    else:
        raise HTTPException(status_code=400, detail="Provide channel_id or message_id")
    return {"status": "deleted"}
