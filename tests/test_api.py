"""API tests for the AutoCraft dashboard (uses mock agent)."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["AUTOCRAFT_API_MOCK"] = "1"
os.environ["AUTOCRAFT_PROVIDER"] = "mock"
os.environ.pop("AUTOCRAFT_API_KEYS", None)
os.environ.pop("AUTOCRAFT_ENV", None)
os.environ.pop("ENVIRONMENT", None)
os.environ.pop("VERCEL", None)

from src.api.app import create_app, _sessions, _teams


@pytest.fixture
def client(tmp_path, monkeypatch):
    _sessions.clear()
    _teams.clear()
    monkeypatch.setenv("AUTOCRAFT_SESSION_DIR", str(tmp_path / "sessions"))
    monkeypatch.delenv("AUTOCRAFT_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    import src.api.app as app_mod
    from src.api.session_store import SessionStore

    app_mod._store = SessionStore(root=str(tmp_path / "sessions"))
    application = create_app()
    with TestClient(application) as test_client:
        yield test_client
    _sessions.clear()
    _teams.clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["auth_required"] is False


def test_chat_persists(client):
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    info = client.get(f"/api/session/{session_id}")
    assert info.status_code == 200
    assert len(info.json()["history"]) >= 2


def test_team_run(client):
    response = client.post("/api/team/run", json={"goal": "Ship feature"})
    assert response.status_code == 200
    assert len(response.json()["steps"]) == 3


def test_plugins_marketplace(client):
    response = client.get("/api/plugins")
    assert response.status_code == 200
    names = {plugin["name"] for plugin in response.json()["plugins"]}
    assert "echo" in names


def test_plugins_install(client):
    response = client.post("/api/plugins/install", json={"name": "summarize"})
    assert response.status_code == 200
    assert response.json()["status"] == "installed"


def test_test_run_no_execute(client):
    response = client.post(
        "/api/test/run", json={"goal": "memory module", "execute": False}
    )
    assert response.status_code == 200
    assert "plan" in response.json()


def test_auth_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOCRAFT_API_KEYS", "secret-key")
    monkeypatch.setenv("AUTOCRAFT_API_MOCK", "1")
    monkeypatch.delenv("AUTOCRAFT_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("AUTOCRAFT_SESSION_DIR", str(tmp_path / "auth-sessions"))
    import src.api.app as app_mod
    from src.api.session_store import SessionStore

    app_mod._store = SessionStore(root=str(tmp_path / "auth-sessions"))
    _sessions.clear()
    with TestClient(create_app()) as test_client:
        denied = test_client.post("/api/chat", json={"message": "x"})
        assert denied.status_code == 401
        accepted = test_client.post(
            "/api/chat",
            json={"message": "x"},
            headers={"X-API-Key": "secret-key"},
        )
        assert accepted.status_code == 200


def test_production_requires_configured_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("AUTOCRAFT_API_KEYS", raising=False)
    monkeypatch.setenv("AUTOCRAFT_ENV", "production")
    monkeypatch.setenv("AUTOCRAFT_SESSION_DIR", str(tmp_path / "production-sessions"))
    import src.api.app as app_mod
    from src.api.session_store import SessionStore

    app_mod._store = SessionStore(root=str(tmp_path / "production-sessions"))
    with TestClient(create_app()) as test_client:
        health = test_client.get("/health")
        assert health.status_code == 200
        assert health.json()["auth_required"] is True
        denied = test_client.post("/api/chat", json={"message": "x"})
        assert denied.status_code == 503


def test_chat_stream_sse(client):
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "hello stream"},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = b"".join(response.iter_bytes()).decode()
    assert "data:" in body
    assert "Mock response" in body or "hello stream" in body
    assert "done" in body
