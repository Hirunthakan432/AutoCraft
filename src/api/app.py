"""FastAPI application for the AutoCraft dashboard."""

from __future__ import annotations

import os
import uuid
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.agent.controller import AgentController, create_agent
from src.agent.orchestrator import MultiAgentOrchestrator, create_team
from src.agent.tester import TestingAgent
from src.api.auth import api_keys_configured, require_api_key
from src.api.session_store import SessionStore, is_valid_session_id
from src.plugins.registry import create_default_registry

load_dotenv()

_sessions: Dict[str, AgentController] = {}
_teams: Dict[str, MultiAgentOrchestrator] = {}
_store = SessionStore()
_plugins = create_default_registry()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    provider: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    history_length: int


class SessionInfo(BaseModel):
    session_id: str
    history: list
    tasks: list
    tools: list


class TeamRunRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    pipeline: Optional[List[str]] = None
    provider: Optional[str] = None
    team_id: Optional[str] = None


class TestRunRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    execute: bool = True
    provider: Optional[str] = None


class PluginAction(BaseModel):
    name: str


def _use_mock() -> bool:
    return os.getenv("AUTOCRAFT_API_MOCK", "").lower() in ("1", "true", "yes")


def _hydrate_agent(session_id: str, agent: AgentController) -> None:
    data = _store.load(session_id)
    if not data:
        return
    agent.memory.history = list(data.get("history") or [])
    # Replace facts instead of appending (avoid duplicates on re-hydrate)
    tasks = list(data.get("tasks") or [])
    agent.memory.facts["tasks"] = tasks


def _persist_agent(session_id: str, agent: AgentController) -> None:
    _store.save(
        session_id,
        history=agent.memory.get_history(),
        tasks=agent.memory.recall("tasks"),
    )


def _get_or_create_agent(
    session_id: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[str, AgentController]:
    if session_id is not None:
        if not is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session id")
        if session_id in _sessions:
            return session_id, _sessions[session_id]

    sid = session_id or str(uuid.uuid4())
    agent = create_agent(use_mock=_use_mock(), provider=provider)
    if session_id:
        _hydrate_agent(sid, agent)
    _sessions[sid] = agent
    return sid, agent


def _get_or_create_team(
    team_id: Optional[str] = None,
    provider: Optional[str] = None,
    pipeline: Optional[List[str]] = None,
) -> tuple[str, MultiAgentOrchestrator]:
    if team_id and team_id in _teams:
        return team_id, _teams[team_id]
    tid = team_id or str(uuid.uuid4())
    team = create_team(use_mock=_use_mock(), provider=provider, pipeline=pipeline)
    _teams[tid] = team
    return tid, team


def create_app() -> FastAPI:
    application = FastAPI(
        title="AutoCraft Dashboard API",
        description="Web API for the AutoCraft agent framework",
        version="0.4.1",
    )

    raw_origins = os.getenv("AUTOCRAFT_CORS_ORIGINS", "*").strip()
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    # Browsers reject credentials + wildcard origin; only enable credentials for explicit origins
    allow_creds = origins != ["*"]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    auth_dep = [Depends(require_api_key)]

    @application.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "provider": os.getenv("AUTOCRAFT_PROVIDER", "gemini"),
            "sessions": len(_sessions),
            "teams": len(_teams),
            "auth_required": api_keys_configured(),
            "persistent_sessions": True,
        }

    @application.get("/api/providers", dependencies=auth_dep)
    def list_providers() -> dict:
        return {
            "providers": ["gemini", "openai", "local", "mock"],
            "default": os.getenv("AUTOCRAFT_PROVIDER", "gemini"),
        }

    @application.post("/api/chat", response_model=ChatResponse, dependencies=auth_dep)
    def chat(body: ChatRequest) -> ChatResponse:
        try:
            sid, agent = _get_or_create_agent(body.session_id, body.provider)
            reply = agent.chat(body.message)
            _persist_agent(sid, agent)
            return ChatResponse(
                session_id=sid,
                response=reply,
                history_length=len(agent.memory.get_history()),
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @application.get("/api/session/{session_id}", response_model=SessionInfo, dependencies=auth_dep)
    def get_session(session_id: str) -> SessionInfo:
        if not is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session id")
        agent = _sessions.get(session_id)
        if agent is None:
            data = _store.load(session_id)
            if data is None:
                raise HTTPException(status_code=404, detail="Session not found")
            return SessionInfo(
                session_id=session_id,
                history=data.get("history") or [],
                tasks=data.get("tasks") or [],
                tools=[],
            )
        return SessionInfo(
            session_id=session_id,
            history=agent.memory.get_history(),
            tasks=agent.memory.recall("tasks"),
            tools=agent.sandbox.list_allowed(),
        )

    @application.post("/api/session/{session_id}/clear", dependencies=auth_dep)
    def clear_session(session_id: str) -> dict:
        if not is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session id")
        agent = _sessions.get(session_id)
        if agent is None and _store.load(session_id) is None:
            raise HTTPException(status_code=404, detail="Session not found")
        if agent:
            agent.clear_session()
            _persist_agent(session_id, agent)
        else:
            _store.save(session_id, history=[], tasks=[])
        return {"status": "cleared", "session_id": session_id}

    @application.delete("/api/session/{session_id}", dependencies=auth_dep)
    def delete_session(session_id: str) -> dict:
        if not is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session id")
        had_memory = session_id in _sessions
        _sessions.pop(session_id, None)
        had_disk = False
        try:
            had_disk = _store.delete(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if not had_memory and not had_disk:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "deleted", "session_id": session_id}

    @application.get("/api/team/roles", dependencies=auth_dep)
    def team_roles() -> dict:
        team = create_team(use_mock=True)
        return {"roles": team.list_roles(), "default_pipeline": list(team.pipeline)}

    @application.post("/api/team/run", dependencies=auth_dep)
    def team_run(body: TeamRunRequest) -> dict:
        try:
            tid, team = _get_or_create_team(body.team_id, body.provider, body.pipeline)
            result = team.run(body.goal, pipeline=body.pipeline)
            payload = result.to_dict()
            payload["team_id"] = tid
            return payload
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @application.post("/api/test/run", dependencies=auth_dep)
    def test_run(body: TestRunRequest) -> dict:
        try:
            tester = TestingAgent(use_mock=_use_mock(), provider=body.provider)
            result = tester.run(body.goal, execute=body.execute)
            return result.to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @application.get("/api/plugins", dependencies=auth_dep)
    def plugins_list() -> dict:
        return {"plugins": _plugins.marketplace()}

    @application.post("/api/plugins/install", dependencies=auth_dep)
    def plugins_install(body: PluginAction) -> dict:
        try:
            info = _plugins.install(body.name)
            return {"status": "installed", "plugin": info.name, "enabled": info.enabled}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @application.post("/api/plugins/enable", dependencies=auth_dep)
    def plugins_enable(body: PluginAction) -> dict:
        try:
            _plugins.enable(body.name)
            return {"status": "enabled", "plugin": body.name}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @application.post("/api/plugins/disable", dependencies=auth_dep)
    def plugins_disable(body: PluginAction) -> dict:
        _plugins.disable(body.name)
        return {"status": "disabled", "plugin": body.name}

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
      --bg: #0f1419; --panel: #1a2332; --border: #2d3a4f; --text: #e7ecf3;
      --muted: #8b9bb4; --accent: #3b82f6; --accent-hover: #2563eb;
      --user: #1e3a5f; --bot: #1a2e1a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; font-family: ui-sans-serif, system-ui, sans-serif;
      background: var(--bg); color: var(--text); min-height: 100vh;
      display: flex; flex-direction: column;
    }
    header {
      padding: 1rem 1.5rem; border-bottom: 1px solid var(--border);
      display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
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
    button {
      padding: 0.75rem 1rem; border: none; border-radius: 10px;
      background: var(--accent); color: white; font-weight: 600; cursor: pointer;
    }
    button.secondary { background: transparent; border: 1px solid var(--border); color: var(--muted); }
    button:disabled { opacity: 0.5; }
  </style>
</head>
<body>
  <header>
    <h1>⚡ AutoCraft</h1>
    <span class="badge" id="status">connecting…</span>
    <span class="badge" id="session">no session</span>
    <button type="button" class="secondary" id="teamBtn">Team</button>
    <button type="button" class="secondary" id="testBtn">Test agent</button>
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
    const apiKey = localStorage.getItem('autocraft_api_key') || '';
    const log = document.getElementById('log');
    const form = document.getElementById('form');
    const input = document.getElementById('input');
    const send = document.getElementById('send');

    function headers() {
      const h = { 'Content-Type': 'application/json' };
      if (apiKey) h['X-API-Key'] = apiKey;
      return h;
    }
    function formatError(j, statusText) {
      if (!j) return statusText || 'Request failed';
      const d = j.detail;
      if (typeof d === 'string') return d;
      if (Array.isArray(d)) return d.map(x => x.msg || JSON.stringify(x)).join('; ');
      if (d != null) return JSON.stringify(d);
      return statusText || 'Request failed';
    }
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
      document.getElementById('session').textContent = id ? ('session ' + id.slice(0, 8) + '…') : 'no session';
    }
    async function refreshHealth() {
      try {
        const j = await (await fetch('/health')).json();
        document.getElementById('status').textContent =
          j.status + ' · ' + j.provider + (j.auth_required ? ' · auth' : '');
      } catch (e) {
        document.getElementById('status').textContent = 'offline';
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
          method: 'POST', headers: headers(),
          body: JSON.stringify({ message, session_id: sessionId }),
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(formatError(j, r.statusText));
        setSession(j.session_id);
        addMsg(j.response, 'bot');
      } catch (err) {
        addMsg('Error: ' + err.message, 'system');
      } finally {
        send.disabled = false; input.focus();
      }
    });
    document.getElementById('teamBtn').addEventListener('click', async () => {
      const goal = input.value.trim() || prompt('Team goal?');
      if (!goal) return;
      input.value = '';
      addMsg('[team] ' + goal, 'user');
      try {
        const r = await fetch('/api/team/run', {
          method: 'POST', headers: headers(), body: JSON.stringify({ goal }),
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(formatError(j, r.statusText));
        for (const s of j.steps || []) addMsg('[' + s.role + ']\n' + s.output, 'bot');
      } catch (err) {
        addMsg('Team error: ' + err.message, 'system');
      }
    });
    document.getElementById('testBtn').addEventListener('click', async () => {
      const goal = input.value.trim() || prompt('What should we test?');
      if (!goal) return;
      input.value = '';
      addMsg('[test] ' + goal, 'user');
      try {
        const r = await fetch('/api/test/run', {
          method: 'POST', headers: headers(),
          body: JSON.stringify({ goal, execute: true }),
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(formatError(j, r.statusText));
        addMsg(j.plan + '\n\n' + j.command + '\n' + (j.command_output || ''), 'bot');
      } catch (err) {
        addMsg('Test error: ' + err.message, 'system');
      }
    });
    document.getElementById('clearBtn').addEventListener('click', async () => {
      if (!sessionId) { log.innerHTML = ''; return; }
      await fetch('/api/session/' + sessionId + '/clear', { method: 'POST', headers: headers() });
      log.innerHTML = '';
      addMsg('Session cleared.', 'system');
    });
    if (sessionId) setSession(sessionId);
    refreshHealth();
    addMsg('Ready. Team / Test agent available. Set localStorage autocraft_api_key if auth is on.', 'system');
  </script>
</body>
</html>
"""
