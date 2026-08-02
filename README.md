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
| Interactive CLI | ✅ |
| Sandboxed tools (files + shell) | ✅ |
| Unified memory (chat + facts) | ✅ |
| Multi-provider abstraction | ✅ Gemini + Mock |
| Plugin registry | 🚧 foundation |
| Web dashboard | 📋 planned |

---

## Features

### Agent engine
- **`AgentController`** — orchestrates LLM, memory, and tools in one place
- **`AgentMemory`** — conversation history plus key/value facts (`remember` / `recall`)
- **Providers** — `GeminiProvider` for production, `MockProvider` for offline tests

### Secure tools
- **ToolSandbox** allow-list — only registered tools can run
- **Workspace isolation** — file paths cannot escape the project root
- **Safe shell** — no `shell=True`; blocked patterns for `rm -rf`, `sudo`, `curl\|bash`, etc.

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

Copy the example env file and add your key:

```bash
cp .env.example .env
# GEMINI_API_KEY=your_google_ai_api_key_here
```

### 3. Run

```bash
# Smoke-test (calls Gemini)
python -m src.main

# Interactive chat
python -m src.cli

# Offline mock agent (no API key)
python -c "from src.agent.controller import create_agent; print(create_agent(use_mock=True).chat('hello'))"

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
 ├── LLMProvider ── GeminiProvider / MockProvider
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
│   ├── llm/             # LLMProvider, Mock, Gemini adapter
│   ├── security/        # ToolSandbox
│   ├── tools/           # workspace-safe file_ops
│   ├── plugins/         # PluginRegistry
│   ├── cli.py           # Interactive session
│   └── main.py          # Smoke-test entrypoint
├── tests/
├── .github/workflows/   # Python CI
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## Usage examples

### Programmatic agent

```python
from src.agent.controller import create_agent

agent = create_agent()  # uses Gemini + default sandbox
print(agent.chat("List the top-level project files."))

# Facts persist for the session
agent.memory.remember("goal", "ship phase 3")
print(agent.memory.recall("goal"))
```

### Custom sandbox / mock LLM

```python
from src.agent.controller import AgentController
from src.llm.provider import MockProvider
from src.security.sandbox import ToolSandbox

sandbox = ToolSandbox()
sandbox.register("ping", lambda: "pong")

agent = AgentController(llm=MockProvider(), sandbox=sandbox)
assert agent.run_tool("ping") == "pong"
print(agent.chat("status check"))
```

---

## Security notes

- Tools only operate inside the process **workspace root** (`cwd` at startup).
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
- [ ] OpenAI / local model providers
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
