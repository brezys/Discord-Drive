from fastapi import HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(request: Request, api_key: str | None = Security(api_key_header)):
    # Skip auth for health and thumbnails (thumbnails are public in MVP)
    if request.url.path in ("/health", "/") or request.url.path.startswith("/thumb/"):
        return
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
