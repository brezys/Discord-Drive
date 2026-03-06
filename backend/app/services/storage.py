"""Thumbnail and optional full-image storage on local disk."""
from __future__ import annotations

import hashlib
import io
import os

from PIL import Image

from app.config import settings


def _ensure_dirs() -> None:
    os.makedirs(settings.thumb_dir, exist_ok=True)
    if settings.store_full_images:
        os.makedirs(settings.image_dir, exist_ok=True)


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_thumbnail(asset_id: str, image_bytes: bytes) -> str:
    """Save a thumbnail and return its relative path."""
    _ensure_dirs()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail(settings.thumb_size, Image.LANCZOS)
    path = os.path.join(settings.thumb_dir, f"{asset_id}.jpg")
    image.save(path, "JPEG", quality=85, optimize=True)
    return path


def save_full_image(asset_id: str, image_bytes: bytes, ext: str = ".jpg") -> str | None:
    if not settings.store_full_images:
        return None
    _ensure_dirs()
    path = os.path.join(settings.image_dir, f"{asset_id}{ext}")
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


def get_image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    image = Image.open(io.BytesIO(image_bytes))
    return image.width, image.height
