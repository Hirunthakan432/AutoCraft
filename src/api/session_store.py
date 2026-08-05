"""Persistent session stores for AutoCraft.

Backends:
  - json  (default) — JSON files under AUTOCRAFT_SESSION_DIR
  - redis           — Redis keys (requires redis package + REDIS_URL)

Select with AUTOCRAFT_SESSION_BACKEND=json|redis
"""

from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def is_valid_session_id(session_id: str) -> bool:
    return bool(session_id and _SAFE_ID.match(session_id))


@runtime_checkable
class SessionStoreBackend(Protocol):
    """Common interface for session persistence backends."""

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        ...

    def save(
        self,
        session_id: str,
        history: List[dict],
        tasks: Optional[List[str]] = None,
        facts: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        ...

    def delete(self, session_id: str) -> bool:
        ...

    def list_ids(self) -> List[str]:
        ...


class JsonSessionStore:
    """Persists chat history per session_id as JSON files on disk."""

    backend_name = "json"

    def __init__(self, root: Optional[str] = None):
        base = root or os.getenv("AUTOCRAFT_SESSION_DIR", ".autocraft/sessions")
        self.root = Path(base).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, session_id: str) -> Path:
        if not is_valid_session_id(session_id):
            raise ValueError("Invalid session id")
        path = (self.root / f"{session_id}.json").resolve()
        try:
            path.relative_to(self.root)
        except ValueError as e:
            raise ValueError("Invalid session id") from e
        return path

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(session_id)
        if not path.exists():
            return None
        with self._lock:
            return json.loads(path.read_text(encoding="utf-8"))

    def save(
        self,
        session_id: str,
        history: List[dict],
        tasks: Optional[List[str]] = None,
        facts: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        path = self._path(session_id)
        payload = {
            "session_id": session_id,
            "history": history,
            "tasks": tasks or [],
            "facts": facts or {},
        }
        with self._lock:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def delete(self, session_id: str) -> bool:
        path = self._path(session_id)
        with self._lock:
            if path.exists():
                path.unlink()
                return True
        return False

    def list_ids(self) -> List[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))


# Backwards-compatible alias
SessionStore = JsonSessionStore


class RedisSessionStore:
    """Persists sessions in Redis (optional production backend).

    Keys: ``{prefix}{session_id}`` → JSON payload
    Index set: ``{prefix}__index`` for list_ids()
    """

    backend_name = "redis"

    def __init__(
        self,
        url: Optional[str] = None,
        *,
        prefix: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        client: Any = None,
    ):
        self.prefix = prefix or os.getenv("AUTOCRAFT_REDIS_PREFIX", "autocraft:session:")
        self.index_key = f"{self.prefix}__index"
        raw_ttl = ttl_seconds
        if raw_ttl is None:
            env_ttl = os.getenv("AUTOCRAFT_SESSION_TTL", "").strip()
            raw_ttl = int(env_ttl) if env_ttl.isdigit() else None
        self.ttl_seconds = raw_ttl

        if client is not None:
            self.client = client
        else:
            try:
                import redis
            except ImportError as e:
                raise RuntimeError(
                    "Redis backend requires the 'redis' package. "
                    "Install with: pip install redis"
                ) from e
            redis_url = url or os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
            self.client = redis.from_url(redis_url, decode_responses=True)

    def _key(self, session_id: str) -> str:
        if not is_valid_session_id(session_id):
            raise ValueError("Invalid session id")
        return f"{self.prefix}{session_id}"

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        key = self._key(session_id)
        raw = self.client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def save(
        self,
        session_id: str,
        history: List[dict],
        tasks: Optional[List[str]] = None,
        facts: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        key = self._key(session_id)
        payload = {
            "session_id": session_id,
            "history": history,
            "tasks": tasks or [],
            "facts": facts or {},
        }
        data = json.dumps(payload)
        pipe = self.client.pipeline()
        if self.ttl_seconds and self.ttl_seconds > 0:
            pipe.set(key, data, ex=self.ttl_seconds)
        else:
            pipe.set(key, data)
        pipe.sadd(self.index_key, session_id)
        pipe.execute()

    def delete(self, session_id: str) -> bool:
        key = self._key(session_id)
        pipe = self.client.pipeline()
        pipe.delete(key)
        pipe.srem(self.index_key, session_id)
        results = pipe.execute()
        return bool(results[0])

    def list_ids(self) -> List[str]:
        members = self.client.smembers(self.index_key) or set()
        return sorted(str(m) for m in members)


def create_session_store(
    backend: Optional[str] = None,
    **kwargs: Any,
) -> SessionStoreBackend:
    """Factory: build a session store from name or AUTOCRAFT_SESSION_BACKEND.

    Defaults to json. Pass backend='redis' or set env to use Redis.
    """
    key = (backend or os.getenv("AUTOCRAFT_SESSION_BACKEND", "json")).strip().lower()
    if key in ("redis", "redis://"):
        return RedisSessionStore(**kwargs)
    if key in ("json", "file", "disk"):
        return JsonSessionStore(**kwargs)
    raise ValueError(f"Unknown session backend '{key}'. Use: json | redis")
