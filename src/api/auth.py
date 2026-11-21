"""API-key authentication for the AutoCraft dashboard API."""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


def _valid_keys() -> tuple[str, ...]:
    raw = os.getenv("AUTOCRAFT_API_KEYS", "").strip()
    if not raw:
        return ()
    return tuple(key.strip() for key in raw.split(",") if key.strip())


def _is_production() -> bool:
    environment = (
        os.getenv("AUTOCRAFT_ENV")
        or os.getenv("ENVIRONMENT")
        or ""
    ).strip().lower()
    return environment == "production" or os.getenv("VERCEL", "").lower() in {
        "1", "true", "yes"
    }


def api_keys_configured() -> bool:
    """Return whether at least one non-empty API key is configured."""
    return bool(_valid_keys())


def auth_required() -> bool:
    """Authentication is mandatory in production, optional for local development."""
    return api_keys_configured() or _is_production()


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """Require a configured key; fail closed when production has no keys."""
    keys = _valid_keys()
    if not keys:
        if _is_production():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API authentication is required but AUTOCRAFT_API_KEYS is not configured",
            )
        return None

    if not x_api_key or not any(
        hmac.compare_digest(x_api_key, configured_key) for configured_key in keys
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
