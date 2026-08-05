import tempfile
from typing import Any, Dict, Optional, Set

import pytest

from src.api.session_store import (
    JsonSessionStore,
    RedisSessionStore,
    SessionStore,
    create_session_store,
    is_valid_session_id,
)


def test_save_load_delete():
    with tempfile.TemporaryDirectory() as tmp:
        store = JsonSessionStore(root=tmp)
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
        with pytest.raises(ValueError):
            store.save("../evil", history=[])
        with pytest.raises(ValueError):
            store.save("a/b", history=[])
        with pytest.raises(ValueError):
            store.save("", history=[])


def test_is_valid_session_id():
    assert is_valid_session_id("abc-123")
    assert is_valid_session_id("uuid_like_01")
    assert not is_valid_session_id("../x")
    assert not is_valid_session_id("")


def test_create_session_store_json(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOCRAFT_SESSION_BACKEND", "json")
    store = create_session_store(root=str(tmp_path / "s"))
    assert isinstance(store, JsonSessionStore)
    assert store.backend_name == "json"


def test_create_session_store_unknown():
    with pytest.raises(ValueError, match="Unknown session backend"):
        create_session_store(backend="mongo")


class _FakeRedis:
    """Minimal redis-like client for unit tests (no real Redis required)."""

    def __init__(self) -> None:
        self._kv: Dict[str, str] = {}
        self._sets: Dict[str, Set[str]] = {}

    def get(self, key: str) -> Optional[str]:
        return self._kv.get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._kv[key] = value
        return True

    def delete(self, key: str) -> int:
        return 1 if self._kv.pop(key, None) is not None else 0

    def sadd(self, key: str, *members: str) -> int:
        s = self._sets.setdefault(key, set())
        before = len(s)
        s.update(members)
        return len(s) - before

    def srem(self, key: str, *members: str) -> int:
        s = self._sets.get(key, set())
        n = 0
        for m in members:
            if m in s:
                s.discard(m)
                n += 1
        return n

    def smembers(self, key: str) -> Set[str]:
        return set(self._sets.get(key, set()))

    def pipeline(self) -> "_FakePipeline":
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, client: _FakeRedis) -> None:
        self.client = client
        self._ops: list = []

    def set(self, key: str, value: str, ex: Optional[int] = None) -> "_FakePipeline":
        self._ops.append(("set", key, value, ex))
        return self

    def delete(self, key: str) -> "_FakePipeline":
        self._ops.append(("delete", key))
        return self

    def sadd(self, key: str, *members: str) -> "_FakePipeline":
        self._ops.append(("sadd", key, members))
        return self

    def srem(self, key: str, *members: str) -> "_FakePipeline":
        self._ops.append(("srem", key, members))
        return self

    def execute(self) -> list:
        results = []
        for op in self._ops:
            if op[0] == "set":
                results.append(self.client.set(op[1], op[2], ex=op[3]))
            elif op[0] == "delete":
                results.append(self.client.delete(op[1]))
            elif op[0] == "sadd":
                results.append(self.client.sadd(op[1], *op[2]))
            elif op[0] == "srem":
                results.append(self.client.srem(op[1], *op[2]))
        self._ops.clear()
        return results


def test_redis_session_store_roundtrip():
    fake = _FakeRedis()
    store = RedisSessionStore(client=fake, prefix="test:sess:")
    store.save(
        "s1",
        history=[{"role": "user", "content": "hello"}],
        tasks=["goal"],
        facts={"tasks": ["goal"]},
    )
    data = store.load("s1")
    assert data is not None
    assert data["history"][0]["content"] == "hello"
    assert data["tasks"] == ["goal"]
    assert data["facts"]["tasks"] == ["goal"]
    assert "s1" in store.list_ids()
    assert store.delete("s1") is True
    assert store.load("s1") is None
    assert "s1" not in store.list_ids()


def test_redis_rejects_bad_id():
    store = RedisSessionStore(client=_FakeRedis())
    with pytest.raises(ValueError):
        store.save("../bad", history=[])


def test_create_session_store_redis_with_client():
    fake = _FakeRedis()
    store = create_session_store(backend="redis", client=fake)
    assert isinstance(store, RedisSessionStore)
    store.save("x", history=[])
    assert store.load("x")["session_id"] == "x"
