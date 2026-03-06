"""In-memory channel registry with optional JSON persistence."""
from __future__ import annotations

import json
import os
from typing import Any

_REGISTRY_PATH = "/app/data/channel_registry.json"
_registry: dict[str, bool] = {}


def _key(guild_id: str, channel_id: str) -> str:
    return f"{guild_id}:{channel_id}"


def _load() -> None:
    global _registry
    try:
        with open(_REGISTRY_PATH) as f:
            _registry = json.load(f)
    except FileNotFoundError:
        _registry = {}


def _save() -> None:
    os.makedirs(os.path.dirname(_REGISTRY_PATH), exist_ok=True)
    with open(_REGISTRY_PATH, "w") as f:
        json.dump(_registry, f)


# Load on import
_load()


def set_channel(guild_id: str, channel_id: str, enabled: bool, admin_id: str = "") -> None:
    _registry[_key(guild_id, channel_id)] = enabled
    _save()


def is_enabled(guild_id: str, channel_id: str) -> bool:
    return _registry.get(_key(guild_id, channel_id), False)


def get_all() -> list[dict[str, Any]]:
    return [
        {"guild_id": k.split(":")[0], "channel_id": k.split(":")[1], "enabled": v}
        for k, v in _registry.items()
    ]
