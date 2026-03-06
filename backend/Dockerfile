FROM python:3.12-slim

WORKDIR /app

# System deps for Pillow / torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Pre-download model weights at build time ──────────────────────────────────
# open_clip uses CLIP_CACHE_DIR for the openai pretrained checkpoint.
# Baking the weights into the image means zero runtime download latency.
ENV CLIP_CACHE_DIR=/app/model_cache
ENV HF_HOME=/app/model_cache
ENV TORCH_HOME=/app/model_cache

RUN python -c "\
import open_clip; \
print('Downloading ViT-B-32 openai weights…'); \
open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai'); \
print('Model download complete')"

# ── App code ──────────────────────────────────────────────────────────────────
COPY app ./app

RUN mkdir -p /app/thumbs /app/images /app/data

# Keep one worker: multiple workers each load the model into RAM independently.
# If you need concurrency, use async endpoints (already the case here).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
