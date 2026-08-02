"""FastAPI application for the AutoCraft dashboard."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.agent.controller import AgentController, create_agent

load_dotenv()

# In-memory sessions (single-process dashboard; swap for Redis later)
_sessions: Dict[str, AgentController] = {}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    session_id: Optional[str] = Field(None, description="Existing session id")
    provider: Optional[str] = Field(
        None, description="Override provider: gemini | openai | local | mock"
    )


class ChatResponse(BaseModel):
    session_id: str
    response: str
    history_length: int


class SessionInfo(BaseModel):
    session_id: str
    history: list
    tasks: list
    tools: list


def _get_or_create_agent(
    session_id: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[str, AgentController]:
    use_mock = os.getenv("AUTOCRAFT_API_MOCK", "").lower() in ("1", "true", "yes")
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    sid = session_id or str(uuid.uuid4())
    agent = create_agent(use_mock=use_mock, provider=provider)
    _sessions[sid] = agent
    return sid, agent


def create_app() -> FastAPI:
    application = FastAPI(
        title="AutoCraft Dashboard API",
        description="Web API for the AutoCraft agent framework",
        version="0.2.0",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("AUTOCRAFT_CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "provider": os.getenv("AUTOCRAFT_PROVIDER", "gemini"),
            "sessions": len(_sessions),
        }

    @application.get("/api/providers")
    def list_providers() -> dict:
        return {
            "providers": ["gemini", "openai", "local", "mock"],
            "default": os.getenv("AUTOCRAFT_PROVIDER", "gemini"),
        }

    @application.post("/api/chat", response_model=ChatResponse)
    def chat(body: ChatRequest) -> ChatResponse:
        try:
            sid, agent = _get_or_create_agent(body.session_id, body.provider)
            reply = agent.chat(body.message)
            return ChatResponse(
                session_id=sid,
                response=reply,
                history_length=len(agent.memory.get_history()),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @application.get("/api/session/{session_id}", response_model=SessionInfo)
    def get_session(session_id: str) -> SessionInfo:
        agent = _sessions.get(session_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionInfo(
            session_id=session_id,
            history=agent.memory.get_history(),
            tasks=agent.memory.recall("tasks"),
            tools=agent.sandbox.list_allowed(),
        )

    @application.post("/api/session/{session_id}/clear")
    def clear_session(session_id: str) -> dict:
        agent = _sessions.get(session_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Session not found")
        agent.clear_session()
        return {"status": "cleared", "session_id": session_id}

    @application.delete("/api/session/{session_id}")
    def delete_session(session_id: str) -> dict:
        if session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        del _sessions[session_id]
        return {"status": "deleted", "session_id": session_id}

    @application.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return _DASHBOARD_HTML

    return application


app = create_app()


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AutoCraft Dashboard</title>
  <style>
    :root {
      --bg: #0f1419;
      --panel: #1a2332;
      --border: #2d3a4f;
      --text: #e7ecf3;
      --muted: #8b9bb4;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --user: #1e3a5f;
      --bot: #1a2e1a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
      background: var(--bg); color: var(--text); min-height: 100vh;
      display: flex; flex-direction: column;
    }
    header {
      padding: 1rem 1.5rem; border-bottom: 1px solid var(--border);
      display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
    }
    header h1 { margin: 0; font-size: 1.25rem; font-weight: 600; }
    header .badge {
      font-size: 0.75rem; color: var(--muted); background: var(--panel);
      padding: 0.2rem 0.6rem; border-radius: 999px; border: 1px solid var(--border);
    }
    main { flex: 1; display: flex; flex-direction: column; max-width: 800px;
           width: 100%; margin: 0 auto; padding: 1rem; }
    #log {
      flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem;
      padding-bottom: 1rem; min-height: 50vh;
    }
    .msg {
      padding: 0.75rem 1rem; border-radius: 12px; max-width: 90%;
      white-space: pre-wrap; line-height: 1.45; font-size: 0.95rem;
    }
    .msg.user { align-self: flex-end; background: var(--user); }
    .msg.bot { align-self: flex-start; background: var(--bot); border: 1px solid var(--border); }
    .msg.system { align-self: center; color: var(--muted); font-size: 0.8rem; }
    form {
      display: flex; gap: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--border);
    }
    input[type=text] {
      flex: 1; padding: 0.75rem 1rem; border-radius: 10px; border: 1px solid var(--border);
      background: var(--panel); color: var(--text); font-size: 1rem;
    }
    input:focus { outline: 2px solid var(--accent); }
    button {
      padding: 0.75rem 1.25rem; border: none; border-radius: 10px;
      background: var(--accent); color: white; font-weight: 600; cursor: pointer;
    }
    button:hover { background: var(--accent-hover); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    button.secondary { background: transparent; border: 1px solid var(--border); color: var(--muted); }
  </style>
</head>
<body>
  <header>
    <h1>⚡ AutoCraft</h1>
    <span class="badge" id="status">connecting…</span>
    <span class="badge" id="session">no session</span>
    <button type="button" class="secondary" id="clearBtn" style="margin-left:auto">Clear</button>
  </header>
  <main>
    <div id="log"></div>
    <form id="form">
      <input type="text" id="input" placeholder="Ask AutoCraft…" autocomplete="off" />
      <button type="submit" id="send">Send</button>
    </form>
  </main>
  <script>
    let sessionId = localStorage.getItem('autocraft_session') || null;
    const log = document.getElementById('log');
    const form = document.getElementById('form');
    const input = document.getElementById('input');
    const send = document.getElementById('send');
    const statusEl = document.getElementById('status');
    const sessionEl = document.getElementById('session');

    function addMsg(text, role) {
      const d = document.createElement('div');
      d.className = 'msg ' + role;
      d.textContent = text;
      log.appendChild(d);
      log.scrollTop = log.scrollHeight;
    }

    function setSession(id) {
      sessionId = id;
      if (id) localStorage.setItem('autocraft_session', id);
      else localStorage.removeItem('autocraft_session');
      sessionEl.textContent = id ? ('session ' + id.slice(0, 8) + '…') : 'no session';
    }

    async function refreshHealth() {
      try {
        const r = await fetch('/health');
        const j = await r.json();
        statusEl.textContent = j.status + ' · ' + j.provider;
      } catch (e) {
        statusEl.textContent = 'offline';
      }
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const message = input.value.trim();
      if (!message) return;
      input.value = '';
      addMsg(message, 'user');
      send.disabled = true;
      try {
        const r = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, session_id: sessionId }),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || r.statusText);
        setSession(j.session_id);
        addMsg(j.response, 'bot');
      } catch (err) {
        addMsg('Error: ' + err.message, 'system');
      } finally {
        send.disabled = false;
        input.focus();
      }
    });

    document.getElementById('clearBtn').addEventListener('click', async () => {
      if (!sessionId) { log.innerHTML = ''; return; }
      try {
        await fetch('/api/session/' + sessionId + '/clear', { method: 'POST' });
        log.innerHTML = '';
        addMsg('Session cleared.', 'system');
      } catch (err) {
        addMsg('Clear failed: ' + err.message, 'system');
      }
    });

    if (sessionId) setSession(sessionId);
    refreshHealth();
    addMsg('Ready. Messages stay in your browser session.', 'system');
  </script>
</body>
</html>
"""
