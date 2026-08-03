"""Persistent session store (JSON files under a data directory)."""

from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def is_valid_session_id(session_id: str) -> bool:
    return bool(session_id and _SAFE_ID.match(session_id))


class SessionStore:
    """Persists chat history per session_id as JSON."""

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
    ) -> None:
        path = self._path(session_id)
        payload = {
            "session_id": session_id,
            "history": history,
            "tasks": tasks or [],
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
