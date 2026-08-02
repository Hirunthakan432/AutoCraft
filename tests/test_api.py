"""API tests for the AutoCraft dashboard (uses mock agent)."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["AUTOCRAFT_API_MOCK"] = "1"
os.environ["AUTOCRAFT_PROVIDER"] = "mock"
os.environ.pop("AUTOCRAFT_API_KEYS", None)

from src.api.app import create_app, _sessions, _teams, _store


@pytest.fixture
def client(tmp_path, monkeypatch):
    _sessions.clear()
    _teams.clear()
    monkeypatch.setenv("AUTOCRAFT_SESSION_DIR", str(tmp_path / "sessions"))
    # rebuild store path
    import src.api.app as app_mod
    from src.api.session_store import SessionStore

    app_mod._store = SessionStore(root=str(tmp_path / "sessions"))
    application = create_app()
    with TestClient(application) as c:
        yield c
    _sessions.clear()
    _teams.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["auth_required"] is False


def test_chat_persists(client):
    r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    info = client.get(f"/api/session/{sid}")
    assert info.status_code == 200
    assert len(info.json()["history"]) >= 2


def test_team_run(client):
    r = client.post("/api/team/run", json={"goal": "Ship feature"})
    assert r.status_code == 200
    assert len(r.json()["steps"]) == 3


def test_plugins_marketplace(client):
    r = client.get("/api/plugins")
    assert r.status_code == 200
    names = {p["name"] for p in r.json()["plugins"]}
    assert "echo" in names


def test_plugins_install(client):
    r = client.post("/api/plugins/install", json={"name": "summarize"})
    assert r.status_code == 200
    assert r.json()["status"] == "installed"


def test_test_run_no_execute(client):
    r = client.post("/api/test/run", json={"goal": "memory module", "execute": False})
    assert r.status_code == 200
    assert "plan" in r.json()


def test_auth_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOCRAFT_API_KEYS", "secret-key")
    monkeypatch.setenv("AUTOCRAFT_API_MOCK", "1")
    monkeypatch.setenv("AUTOCRAFT_SESSION_DIR", str(tmp_path / "s"))
    import src.api.app as app_mod
    from src.api.session_store import SessionStore

    app_mod._store = SessionStore(root=str(tmp_path / "s"))
    _sessions.clear()
    with TestClient(create_app()) as c:
        denied = c.post("/api/chat", json={"message": "x"})
        assert denied.status_code == 401
        ok = c.post(
            "/api/chat",
            json={"message": "x"},
            headers={"X-API-Key": "secret-key"},
        )
        assert ok.status_code == 200
    monkeypatch.delenv("AUTOCRAFT_API_KEYS", raising=False)
