"""Simple API-key authentication for the dashboard API."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException, status


def api_keys_configured() -> bool:
    raw = os.getenv("AUTOCRAFT_API_KEYS", "").strip()
    return bool(raw)


def _valid_keys() -> set[str]:
    raw = os.getenv("AUTOCRAFT_API_KEYS", "").strip()
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


async def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Optional[str]:
    """If AUTOCRAFT_API_KEYS is set, require a matching X-API-Key header.

    When unset, auth is disabled (local/dev mode).
    """
    keys = _valid_keys()
    if not keys:
        return None
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
