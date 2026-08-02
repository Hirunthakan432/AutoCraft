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
| Sandboxed tools (files + shell) | ✅ |
| Unified memory (chat + facts) | ✅ |
| Multi-provider factory | ✅ |
| Plugin registry | 🚧 foundation |
| Web dashboard | 📋 planned |

---

## Features

### Agent engine
- **`AgentController`** — orchestrates LLM, memory, and tools in one place
- **`AgentMemory`** — conversation history plus key/value facts (`remember` / `recall`)
- **Providers** — Gemini, OpenAI, local (Ollama-compatible), and Mock

### Secure tools
- **ToolSandbox** allow-list — only registered tools can run
- **Workspace isolation** — file paths cannot escape the project root
- **Safe shell** — no `shell=True`; blocked patterns for dangerous commands

### Developer experience
- Interactive CLI with `/clear` and session memory
- Pytest suite (memory, sandbox, controller, providers)
- GitHub Actions CI on every push and PR

---

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/Hirunthakan432/AutoCraft.git
cd AutoCraft
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Pick a provider and set keys:

```env
AUTOCRAFT_PROVIDER=gemini   # gemini | openai | local | mock
GEMINI_API_KEY=...
# OPENAI_API_KEY=...
# LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1
# LOCAL_LLM_MODEL=llama3.2
```

### 3. Run

```bash
# Smoke-test
python -m src.main

# Interactive chat
python -m src.cli

# Offline mock (no API key)
python -c "from src.agent.controller import create_agent; print(create_agent(use_mock=True).chat('hello'))"

# Explicit provider
python -c "from src.agent.controller import create_agent; print(create_agent(provider='openai').chat('hi'))"

# Tests
pytest -v
```

---

## Architecture

```text
User
 │
 ▼
AgentController
 ├── LLMProvider ── Gemini | OpenAI | Local | Mock
 ├── AgentMemory ── history + facts
 ├── ToolSandbox ── allow-list + command policy
 │       └── tools (list_files, read_file, write_file, run_command)
 └── Plugins (registry foundation)
```

### Layout

```text
AutoCraft/
├── src/
│   ├── agent/           # AgentController, create_agent()
│   ├── core/            # GeminiClient, AgentMemory
│   ├── llm/             # Providers + factory
│   ├── security/        # ToolSandbox
│   ├── tools/           # workspace-safe file_ops
│   ├── plugins/         # PluginRegistry
│   ├── cli.py
│   └── main.py
├── tests/
├── .github/workflows/
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## Providers

| Name | Env | Notes |
|------|-----|--------|
| `gemini` | `GEMINI_API_KEY` | Default. Uses `google-genai` + tool calling |
| `openai` | `OPENAI_API_KEY`, optional `OPENAI_MODEL` | Chat Completions API |
| `local` | `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL` | Ollama / LM Studio / vLLM compatible |
| `mock` | — | Offline tests |

Switch with `AUTOCRAFT_PROVIDER` or `create_agent(provider="openai")`.

---

## Usage examples

```python
from src.agent.controller import create_agent

agent = create_agent()  # AUTOCRAFT_PROVIDER or gemini
print(agent.chat("List the top-level project files."))

agent.memory.remember("goal", "ship phase 3")
print(agent.memory.recall("goal"))
```

```python
from src.agent.controller import AgentController
from src.llm.provider import MockProvider
from src.security.sandbox import ToolSandbox

sandbox = ToolSandbox()
sandbox.register("ping", lambda: "pong")
agent = AgentController(llm=MockProvider(), sandbox=sandbox)
assert agent.run_tool("ping") == "pong"
```

---

## Security notes

- Tools only operate inside the process **workspace root**.
- `run_command` uses `shlex.split` + `shell=False` and a blocked-command policy.
- Unregistered tools are denied by `ToolSandbox`.
- Never commit `.env` — it is gitignored.

---

## Roadmap

- [x] Gemini AI integration
- [x] Tool registry + ToolSandbox
- [x] Unified agent memory
- [x] AgentController workflow
- [x] Multi-provider abstraction (Gemini + Mock)
- [x] OpenAI / local model providers
- [ ] Multi-agent collaboration
- [ ] Web dashboard API
- [ ] Plugin marketplace
- [ ] Automated testing agent

---

## Contributing

1. Fork the repository  
2. Create a feature branch  
3. Add tests for new behaviour  
4. Open a pull request  

CI must pass before merge.

---

## License

Released under the [MIT License](LICENSE).
