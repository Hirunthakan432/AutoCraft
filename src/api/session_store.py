"""Persistent session store (JSON files under a data directory)."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionStore:
    """Persists chat history per session_id as JSON."""

    def __init__(self, root: Optional[str] = None):
        base = root or os.getenv("AUTOCRAFT_SESSION_DIR", ".autocraft/sessions")
        self.root = Path(base).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, session_id: str) -> Path:
        # Prevent path traversal
        safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if not safe:
            raise ValueError("Invalid session id")
        return self.root / f"{safe}.json"

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(session_id)
        if not path.exists():
            return None
        with self._lock:
            return json.loads(path.read_text(encoding="utf-8"))

    def save(self, session_id: str, history: List[dict], tasks: Optional[List[str]] = None) -> None:
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
