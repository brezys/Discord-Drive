import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter(tags=["thumbnails"])


@router.get("/thumb/{asset_id}")
async def get_thumbnail(asset_id: str):
    # Sanitize asset_id to prevent path traversal
    if not asset_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid asset ID")

    path = os.path.join(settings.thumb_dir, f"{asset_id}.jpg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(path, media_type="image/jpeg")
