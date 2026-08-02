# ⚡ AutoCraft

> An intelligent AI agent framework for automated software development workflows.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![CI](https://github.com/Hirunthakan432/AutoCraft/actions/workflows/python-ci.yml/badge.svg)](https://github.com/Hirunthakan432/AutoCraft/actions/workflows/python-ci.yml)

---

## Overview

**AutoCraft** is an agentic AI framework for software engineering automation: chat agents, multi-agent teams, sandboxed tools, plugins, and a web dashboard — with pluggable LLM backends.

| Capability | Status |
|------------|--------|
| Gemini / OpenAI / local (Ollama) providers | ✅ |
| Interactive CLI | ✅ |
| Web dashboard + REST API | ✅ |
| Sandboxed tools (files + shell) | ✅ |
| Unified memory (chat + facts) | ✅ |
| Multi-agent teams (planner → coder → reviewer) | ✅ |
| Plugin marketplace | ✅ |
| Automated testing agent | ✅ |
| API key auth + persistent sessions | ✅ |

---

## Quick start

```bash
git clone https://github.com/Hirunthakan432/AutoCraft.git
cd AutoCraft
pip install -r requirements.txt
cp .env.example .env
# set GEMINI_API_KEY (and/or OPENAI_API_KEY / local URL)
```

### CLI

```bash
python -m src.main     # smoke-test
python -m src.cli      # interactive chat
pytest -v              # test suite
```

### Web dashboard

```bash
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

Open **http://127.0.0.1:8000/**

- **Send** — single-agent chat  
- **Team** — planner → coder → reviewer  
- **Test agent** — propose + run pytest  

Offline UI without cloud keys:

```env
AUTOCRAFT_API_MOCK=1
```

---

## Architecture

```text
User (CLI / Browser)
        │
        ▼
   FastAPI (src/api)
        │
        ▼
 AgentController / MultiAgentOrchestrator / TestingAgent
 ├── LLMProvider ── Gemini | OpenAI | Local | Mock
 ├── AgentMemory ── history + facts (persisted on disk)
 ├── ToolSandbox ── allow-list + blocked commands
 └── PluginRegistry ── marketplace install / enable
```

### Layout

```text
AutoCraft/
├── src/
│   ├── agent/          # controller, roles, orchestrator, tester
│   ├── api/            # FastAPI app, auth, session store
│   ├── core/           # Gemini client, memory
│   ├── llm/            # providers + factory
│   ├── security/       # ToolSandbox
│   ├── tools/          # workspace-safe file_ops
│   ├── plugins/        # marketplace registry
│   ├── cli.py
│   └── main.py
├── tests/
├── .github/workflows/
├── requirements.txt
└── .env.example
```

---

## Providers

| Name | Configuration |
|------|----------------|
| `gemini` (default) | `GEMINI_API_KEY` |
| `openai` | `OPENAI_API_KEY`, optional `OPENAI_MODEL` |
| `local` | `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL` |
| `mock` | no key (tests / offline) |

```python
from src.agent.controller import create_agent

agent = create_agent(provider="openai")  # or AUTOCRAFT_PROVIDER env
print(agent.chat("hello"))
```

---

## Multi-agent teams

Default pipeline: **planner → coder → reviewer**  
Roles also include `researcher` and `tester`.

```python
from src.agent.orchestrator import create_team

team = create_team(provider="gemini")
result = team.run("Add rate limiting to the API")
print(result.final)
for step in result.steps:
    print(step.role, "→", step.output[:100])
```

```bash
curl -X POST http://127.0.0.1:8000/api/team/run \
  -H 'Content-Type: application/json' \
  -d '{"goal": "Ship a health endpoint"}'
```

---

## Testing agent

```python
from src.agent.tester import TestingAgent

tester = TestingAgent(use_mock=True)
result = tester.run("cover AgentMemory", execute=False)
print(result.plan, result.command)
```

```bash
curl -X POST http://127.0.0.1:8000/api/test/run \
  -H 'Content-Type: application/json' \
  -d '{"goal": "memory module", "execute": true}'
```

---

## Plugin marketplace

Built-in catalog: `echo`, `summarize`, `lint_hint`.

```bash
curl http://127.0.0.1:8000/api/plugins
curl -X POST http://127.0.0.1:8000/api/plugins/install \
  -H 'Content-Type: application/json' -d '{"name": "summarize"}'
```

```python
from src.plugins.registry import create_default_registry

reg = create_default_registry()
reg.install("summarize")
print(reg.run("summarize", "line one\nline two"))
```

---

## REST API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, provider, auth flag |
| `GET` | `/api/providers` | Backends |
| `POST` | `/api/chat` | Single-agent chat |
| `GET` | `/api/session/{id}` | History / tasks |
| `POST` | `/api/session/{id}/clear` | Clear history |
| `DELETE` | `/api/session/{id}` | Delete session |
| `GET` | `/api/team/roles` | Role catalog |
| `POST` | `/api/team/run` | Multi-agent pipeline |
| `POST` | `/api/test/run` | Testing agent |
| `GET` | `/api/plugins` | Marketplace |
| `POST` | `/api/plugins/install` | Install plugin |
| `POST` | `/api/plugins/enable` | Enable plugin |
| `POST` | `/api/plugins/disable` | Disable plugin |
| `GET` | `/` | Chat UI |

### Auth & sessions

```env
# Optional — when set, all /api/* routes require header X-API-Key
AUTOCRAFT_API_KEYS=dev-key-1,dev-key-2

# JSON session files (default)
AUTOCRAFT_SESSION_DIR=.autocraft/sessions
```

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key-1' \
  -d '{"message": "hello"}'
```

In the browser UI, set `localStorage.autocraft_api_key` if auth is enabled.

---

## Security

- File tools are limited to the process **workspace root**
- `run_command` uses `shell=False` + blocked-command patterns
- `ToolSandbox` allow-list only
- Session IDs are validated (no path traversal)
- Do not expose the API publicly without `AUTOCRAFT_API_KEYS`
- Never commit `.env`

---

## Roadmap

- [x] Gemini AI integration
- [x] Tool registry + ToolSandbox
- [x] Unified agent memory
- [x] AgentController workflow
- [x] Multi-provider abstraction (Gemini + OpenAI + local + Mock)
- [x] Web dashboard API
- [x] Multi-agent collaboration
- [x] Plugin marketplace
- [x] Automated testing agent
- [x] API auth + persistent sessions
- [ ] Richer plugin packaging (entry points / pip packages)
- [ ] Redis / DB-backed session store
- [ ] Streaming responses (SSE / WebSocket)

---

## Contributing

1. Fork → feature branch  
2. Add tests  
3. Open a PR — CI must pass  

## License

[MIT](LICENSE)
