# ⚡ AutoCraft

> An intelligent AI agent framework for automated software development workflows.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![CI](https://github.com/Hirunthakan432/AutoCraft/actions/workflows/python-ci.yml/badge.svg)](https://github.com/Hirunthakan432/AutoCraft/actions/workflows/python-ci.yml)

---

## Overview

**AutoCraft** is an agentic AI framework that helps automate software engineering tasks — scaffolding, code assistance, file operations, and workflow automation — through a secure tool layer and pluggable LLM providers.

| Capability | Status |
|------------|--------|
| Gemini-powered agent | ✅ |
| OpenAI / compatible APIs | ✅ |
| Local models (Ollama, etc.) | ✅ |
| Interactive CLI | ✅ |
| **Web dashboard API** | ✅ |
| Sandboxed tools (files + shell) | ✅ |
| Unified memory (chat + facts) | ✅ |
| Multi-provider factory | ✅ |
| Plugin registry | 🚧 foundation |
| Multi-agent collaboration | 📋 planned |

---

## Quick start

```bash
git clone https://github.com/Hirunthakan432/AutoCraft.git
cd AutoCraft
pip install -r requirements.txt
cp .env.example .env
# set GEMINI_API_KEY (or OPENAI_API_KEY / local URL)
```

### CLI

```bash
python -m src.main          # smoke-test
python -m src.cli           # interactive chat
pytest -v                   # tests
```

### Web dashboard

```bash
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

Open **http://127.0.0.1:8000/** for the UI, or use the REST API:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness + provider |
| `GET` | `/api/providers` | Available backends |
| `POST` | `/api/chat` | `{ "message", "session_id?", "provider?" }` |
| `GET` | `/api/session/{id}` | History, tasks, tools |
| `POST` | `/api/session/{id}/clear` | Clear chat history |
| `DELETE` | `/api/session/{id}` | Drop session |

Set `AUTOCRAFT_API_MOCK=1` to drive the UI without API keys.

---

## Architecture

```text
User (CLI / Browser)
 │
 ▼
AgentController  ◄── FastAPI (src/api)
 ├── LLMProvider ── Gemini | OpenAI | Local | Mock
 ├── AgentMemory ── history + facts
 ├── ToolSandbox ── allow-list + command policy
 └── Plugins
```

---

## Providers

| Name | Env |
|------|-----|
| `gemini` (default) | `GEMINI_API_KEY` |
| `openai` | `OPENAI_API_KEY`, optional `OPENAI_MODEL` |
| `local` | `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL` |
| `mock` | — |

```python
from src.agent.controller import create_agent
agent = create_agent(provider="openai")
print(agent.chat("hello"))
```

---

## Security notes

- Tools only operate inside the process workspace root.
- Shell runs without `shell=True` and with a blocked-command policy.
- Unregistered tools are denied by `ToolSandbox`.
- Dashboard sessions are in-memory (single process); do not expose publicly without auth.
- Never commit `.env`.

---

## Roadmap

- [x] Gemini AI integration
- [x] Tool registry + ToolSandbox
- [x] Unified agent memory
- [x] AgentController workflow
- [x] Multi-provider abstraction
- [x] OpenAI / local model providers
- [x] Web dashboard API
- [ ] Multi-agent collaboration
- [ ] Plugin marketplace
- [ ] Automated testing agent
- [ ] Auth + persistent sessions for the API

---

## Contributing

1. Fork → feature branch → tests → PR  
2. CI must pass before merge

## License

[MIT](LICENSE)
