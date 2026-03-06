from __future__ import annotations

import mimetypes
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import embedder, storage, vector_db

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/discord")
async def ingest_discord_image(
    guild_id: str = Form(...),
    channel_id: str = Form(...),
    message_id: str = Form(...),
    attachment_id: str = Form(...),
    filename: str = Form(...),
    author_id: str = Form(""),
    created_at: str = Form(...),
    image: UploadFile = File(...),
):
    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty image file")

    # Deduplicate by content hash
    content_hash = storage.content_hash(image_bytes)
    if vector_db.asset_exists_by_hash(content_hash):
        return {"asset_id": None, "status": "duplicate"}

    asset_id = str(uuid.uuid4())

    # Determine extension
    ext = os.path.splitext(filename)[1].lower() or ".jpg"

    # Save thumbnail
    thumb_path = storage.save_thumbnail(asset_id, image_bytes)

    # Optionally save full image
    image_path = storage.save_full_image(asset_id, image_bytes, ext)

    # Get dimensions
    try:
        width, height = storage.get_image_dimensions(image_bytes)
    except Exception:
        width, height = 0, 0

    # Generate embedding
    embedding = embedder.embed_image(image_bytes)

    # Build payload
    payload = {
        "asset_id": asset_id,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "message_id": message_id,
        "attachment_id": attachment_id,
        "attachment_filename": filename,
        "author_id": author_id,
        "created_at": created_at,
        "content_hash": content_hash,
        "thumb_path": thumb_path,
        "image_path": image_path,
        "mime_type": image.content_type or mimetypes.guess_type(filename)[0] or "image/jpeg",
        "width": width,
        "height": height,
    }

    vector_db.upsert_asset(asset_id, embedding, payload)

    return {"asset_id": asset_id, "status": "indexed"}
