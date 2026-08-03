"""Smoke tests for the frontend static site."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app, _FRONTEND_DIR, _sessions, _teams


def test_frontend_files_exist():
    assert _FRONTEND_DIR.is_dir()
    assert (_FRONTEND_DIR / "index.html").is_file()
    assert (_FRONTEND_DIR / "styles.css").is_file()
    assert (_FRONTEND_DIR / "app.js").is_file()


@pytest.fixture
def client(tmp_path, monkeypatch):
    _sessions.clear()
    _teams.clear()
    monkeypatch.setenv("AUTOCRAFT_API_MOCK", "1")
    monkeypatch.setenv("AUTOCRAFT_PROVIDER", "mock")
    monkeypatch.delenv("AUTOCRAFT_API_KEYS", raising=False)
    monkeypatch.setenv("AUTOCRAFT_SESSION_DIR", str(tmp_path / "sessions"))
    import src.api.app as app_mod
    from src.api.session_store import SessionStore

    app_mod._store = SessionStore(root=str(tmp_path / "sessions"))
    application = create_app()
    with TestClient(application) as c:
        yield c
    _sessions.clear()
    _teams.clear()


def test_root_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"AutoCraft" in r.content


def test_static_assets(client):
    css = client.get("/static/styles.css")
    assert css.status_code == 200
    assert "--accent" in css.text or ":root" in css.text

    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert "api/chat" in js.text
