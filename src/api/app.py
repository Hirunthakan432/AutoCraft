"""FastAPI application for the AutoCraft dashboard."""

from __future__ import annotations

import os
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
import json
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agent.controller import AgentController, create_agent
from src.agent.orchestrator import MultiAgentOrchestrator, create_team
from src.agent.tester import TestingAgent
from src.api.auth import api_keys_configured, require_api_key
from src.api.session_store import create_session_store, is_valid_session_id
from src.plugins.registry import create_default_registry

load_dotenv()

# Repo root: src/api/app.py -> parents[2] == project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"


def _max_sessions() -> int:
    try:
        return max(1, int(os.getenv("AUTOCRAFT_MAX_SESSIONS", "100")))
    except ValueError:
        return 100


def _max_teams() -> int:
    try:
        return max(1, int(os.getenv("AUTOCRAFT_MAX_TEAMS", "50")))
    except ValueError:
        return 50


# OrderedDict used as simple LRU: move_to_end on access; popitem(last=False) on overflow
_sessions: OrderedDict[str, AgentController] = OrderedDict()
_teams: OrderedDict[str, MultiAgentOrchestrator] = OrderedDict()
_store = create_session_store()
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
    facts = data.get("facts")
    if isinstance(facts, dict) and facts:
        agent.memory.facts = {k: list(v) for k, v in facts.items()}
    else:
        tasks = list(data.get("tasks") or [])
        agent.memory.facts = {"tasks": tasks} if tasks else {}


def _persist_agent(session_id: str, agent: AgentController) -> None:
    _store.save(
        session_id,
        history=agent.memory.get_history(),
        tasks=agent.memory.recall("tasks"),
        facts=dict(agent.memory.facts),
    )


def _touch_session(session_id: str) -> None:
    if session_id in _sessions:
        _sessions.move_to_end(session_id)


def _store_session(session_id: str, agent: AgentController) -> None:
    _sessions[session_id] = agent
    _sessions.move_to_end(session_id)
    while len(_sessions) > _max_sessions():
        # Evict least-recently-used; disk store still holds history
        _sessions.popitem(last=False)


def _store_team(team_id: str, team: MultiAgentOrchestrator) -> None:
    _teams[team_id] = team
    _teams.move_to_end(team_id)
    while len(_teams) > _max_teams():
        _teams.popitem(last=False)


def _get_or_create_agent(
    session_id: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[str, AgentController]:
    if session_id is not None:
        if not is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session id")
        if session_id in _sessions:
            _touch_session(session_id)
            return session_id, _sessions[session_id]

    sid = session_id or str(uuid.uuid4())
    agent = create_agent(use_mock=_use_mock(), provider=provider)
    if session_id:
        _hydrate_agent(sid, agent)
    # Register a persistence callback so run() always writes state to disk.
    # This ensures memory survives even when run() is called directly (e.g.
    # by the orchestrator) rather than only through the API chat handler.
    agent.set_persistence_callback(lambda: _persist_agent(sid, agent))
    _store_session(sid, agent)
    return sid, agent


def _get_or_create_team(
    team_id: Optional[str] = None,
    provider: Optional[str] = None,
    pipeline: Optional[List[str]] = None,
) -> tuple[str, MultiAgentOrchestrator]:
    if team_id and team_id in _teams:
        _teams.move_to_end(team_id)
        return team_id, _teams[team_id]
    tid = team_id or str(uuid.uuid4())
    team = create_team(use_mock=_use_mock(), provider=provider, pipeline=pipeline)
    _store_team(tid, team)
    return tid, team


def create_app() -> FastAPI:
    application = FastAPI(
        title="AutoCraft Dashboard API",
        description="Web API for the AutoCraft agent framework",
        version="0.7.0",
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
        backend = getattr(_store, "backend_name", os.getenv("AUTOCRAFT_SESSION_BACKEND", "json"))
        return {
            "status": "ok",
            "provider": os.getenv("AUTOCRAFT_PROVIDER", "gemini"),
            "sessions": len(_sessions),
            "teams": len(_teams),
            "auth_required": api_keys_configured(),
            "persistent_sessions": True,
            "session_backend": backend,
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
            # The persistence callback registered in _get_or_create_agent handles
            # writing to disk on every run() call, so this explicit call is
            # technically redundant but kept as a safety net.
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

    @application.post("/api/chat/stream", dependencies=auth_dep)
    def chat_stream(body: ChatRequest) -> StreamingResponse:
        """Server-Sent Events stream of chat tokens.

        Events:
          data: {"token": "..."}     — incremental text
          data: {"error": "..."}     — failure mid-stream
          data: {"done": true, "session_id": "...", "response": "..."}
        """
        try:
            sid, agent = _get_or_create_agent(body.session_id, body.provider)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        def event_gen():
            chunks: list[str] = []
            try:
                for chunk in agent.stream(body.message):
                    chunks.append(chunk)
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
                full = "".join(chunks)
                # Persistence is handled by the agent stream() callback;
                # keep an explicit save as a safety net.
                _persist_agent(sid, agent)
                yield f"data: {json.dumps({'done': True, 'session_id': sid, 'response': full})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @application.get("/api/session/{session_id}", response_model=SessionInfo, dependencies=auth_dep)
    def get_session(session_id: str) -> SessionInfo:
        if not is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session id")
        agent = _sessions.get(session_id)
        if agent is not None:
            _touch_session(session_id)
            return SessionInfo(
                session_id=session_id,
                history=agent.memory.get_history(),
                tasks=agent.memory.recall("tasks"),
                tools=agent.sandbox.list_allowed(),
            )
        data = _store.load(session_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionInfo(
            session_id=session_id,
            history=data.get("history") or [],
            tasks=data.get("tasks") or [],
            tools=[],
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
        try:
            _plugins.disable(body.name)
            return {"status": "disabled", "plugin": body.name}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    # --- Frontend (static site) -------------------------------------------
    if _FRONTEND_DIR.is_dir():
        application.mount(
            "/static",
            StaticFiles(directory=str(_FRONTEND_DIR)),
            name="static",
        )

        @application.get("/")
        def dashboard() -> FileResponse:
            index = _FRONTEND_DIR / "index.html"
            if not index.is_file():
                raise HTTPException(status_code=404, detail="Frontend not found")
            return FileResponse(index)
    else:

        @application.get("/")
        def dashboard_missing() -> dict:
            return {
                "error": "Frontend not installed",
                "hint": "Expected frontend/ directory at project root",
            }

    return application


app = create_app()
