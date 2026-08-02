"""API tests for the AutoCraft dashboard (uses mock agent)."""

import os

import pytest
from fastapi.testclient import TestClient

# Force mock provider before app import side effects
os.environ["AUTOCRAFT_API_MOCK"] = "1"
os.environ["AUTOCRAFT_PROVIDER"] = "mock"

from src.api.app import create_app, _sessions


@pytest.fixture
def client():
    _sessions.clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    _sessions.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "provider" in data


def test_providers(client):
    r = client.get("/api/providers")
    assert r.status_code == 200
    names = r.json()["providers"]
    assert "gemini" in names
    assert "mock" in names


def test_chat_creates_session(client):
    r = client.post("/api/chat", json={"message": "hello agent"})
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert "Mock response" in data["response"] or data["response"]
    assert data["history_length"] >= 2


def test_chat_continues_session(client):
    r1 = client.post("/api/chat", json={"message": "first"})
    sid = r1.json()["session_id"]
    r2 = client.post("/api/chat", json={"message": "second", "session_id": sid})
    assert r2.status_code == 200
    assert r2.json()["session_id"] == sid
    assert r2.json()["history_length"] >= 4


def test_get_session(client):
    r = client.post("/api/chat", json={"message": "ping"})
    sid = r.json()["session_id"]
    info = client.get(f"/api/session/{sid}")
    assert info.status_code == 200
    body = info.json()
    assert body["session_id"] == sid
    assert len(body["history"]) >= 2
    assert "list_files" in body["tools"]


def test_clear_session(client):
    r = client.post("/api/chat", json={"message": "x"})
    sid = r.json()["session_id"]
    c = client.post(f"/api/session/{sid}/clear")
    assert c.status_code == 200
    info = client.get(f"/api/session/{sid}").json()
    assert info["history"] == []


def test_delete_session(client):
    r = client.post("/api/chat", json={"message": "bye"})
    sid = r.json()["session_id"]
    d = client.delete(f"/api/session/{sid}")
    assert d.status_code == 200
    assert client.get(f"/api/session/{sid}").status_code == 404


def test_dashboard_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "AutoCraft" in r.text
