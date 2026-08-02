import tempfile
from pathlib import Path

from src.api.session_store import SessionStore


def test_save_load_delete():
    with tempfile.TemporaryDirectory() as tmp:
        store = SessionStore(root=tmp)
        store.save("abc-123", history=[{"role": "user", "content": "hi"}], tasks=["t1"])
        data = store.load("abc-123")
        assert data["history"][0]["content"] == "hi"
        assert data["tasks"] == ["t1"]
        assert "abc-123" in store.list_ids()
        assert store.delete("abc-123") is True
        assert store.load("abc-123") is None


def test_rejects_bad_id():
    with tempfile.TemporaryDirectory() as tmp:
        store = SessionStore(root=tmp)
        try:
            store.save("../evil", history=[])
            assert False
        except ValueError:
            pass
