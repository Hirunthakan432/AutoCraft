"""API tests for the AutoCraft dashboard (uses mock agent)."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["AUTOCRAFT_API_MOCK"] = "1"
os.environ["AUTOCRAFT_PROVIDER"] = "mock"

from src.api.app import create_app, _sessions, _teams


@pytest.fixture
def client():
    _sessions.clear()
    _teams.clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    _sessions.clear()
    _teams.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "teams" in data


def test_providers(client):
    r = client.get("/api/providers")
    assert r.status_code == 200
    names = r.json()["providers"]
    assert "gemini" in names


def test_chat_creates_session(client):
    r = client.post("/api/chat", json={"message": "hello agent"})
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data["history_length"] >= 2


def test_chat_continues_session(client):
    r1 = client.post("/api/chat", json={"message": "first"})
    sid = r1.json()["session_id"]
    r2 = client.post("/api/chat", json={"message": "second", "session_id": sid})
    assert r2.json()["session_id"] == sid
    assert r2.json()["history_length"] >= 4


def test_get_session(client):
    r = client.post("/api/chat", json={"message": "ping"})
    sid = r.json()["session_id"]
    info = client.get(f"/api/session/{sid}")
    assert info.status_code == 200
    assert "list_files" in info.json()["tools"]


def test_clear_session(client):
    r = client.post("/api/chat", json={"message": "x"})
    sid = r.json()["session_id"]
    assert client.post(f"/api/session/{sid}/clear").status_code == 200
    assert client.get(f"/api/session/{sid}").json()["history"] == []


def test_delete_session(client):
    r = client.post("/api/chat", json={"message": "bye"})
    sid = r.json()["session_id"]
    assert client.delete(f"/api/session/{sid}").status_code == 200
    assert client.get(f"/api/session/{sid}").status_code == 404


def test_dashboard_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "AutoCraft" in r.text


def test_team_roles(client):
    r = client.get("/api/team/roles")
    assert r.status_code == 200
    names = {x["name"] for x in r.json()["roles"]}
    assert "planner" in names and "coder" in names


def test_team_run(client):
    r = client.post("/api/team/run", json={"goal": "Add health check endpoint"})
    assert r.status_code == 200
    data = r.json()
    assert data["goal"] == "Add health check endpoint"
    assert len(data["steps"]) == 3
    assert data["steps"][0]["role"] == "planner"
    assert "team_id" in data
