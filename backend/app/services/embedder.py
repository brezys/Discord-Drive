"""
Multimodal embedding service using OpenCLIP.
Both image and text are embedded into the same vector space.
"""
from __future__ import annotations

import io
import logging
from functools import lru_cache
from typing import Any

import open_clip
import torch
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model() -> tuple[Any, Any, Any]:
    """Load model, tokenizer, and preprocessing transform (cached)."""
    model, _, preprocess = open_clip.create_model_and_transforms(
        settings.embed_model, pretrained=settings.embed_pretrained
    )
    tokenizer = open_clip.get_tokenizer(settings.embed_model)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    return model, preprocess, tokenizer


def _device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def embed_image(image_bytes: bytes) -> list[float]:
    model, preprocess, _ = _load_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = preprocess(image).unsqueeze(0).to(_device())
    with torch.no_grad():
        features = model.encode_image(tensor)
        features = features / features.norm(dim=-1, keepdim=True)
    return features[0].cpu().tolist()


def warmup() -> None:
    """Eagerly load the model and run one dummy inference to warm JIT kernels.

    Called once at startup so the first real user query is fast.
    """
    logger.info("[embedder] Loading model and running warmup inference…")
    model, _, tokenizer = _load_model()
    tokens = tokenizer(["warmup"]).to(_device())
    with torch.no_grad():
        _ = model.encode_text(tokens)
    logger.info("[embedder] Warmup complete")


def embed_text(text: str) -> list[float]:
    model, _, tokenizer = _load_model()
    tokens = tokenizer([text]).to(_device())
    with torch.no_grad():
        features = model.encode_text(tokens)
        features = features / features.norm(dim=-1, keepdim=True)
    return features[0].cpu().tolist()
