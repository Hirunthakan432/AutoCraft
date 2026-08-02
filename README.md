# ⚡ AutoCraft

> An intelligent AI agent framework for automated software development workflows.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

---

## 🚀 Overview

**AutoCraft** is an agentic AI framework designed to automate software engineering tasks using AI models, tools, and intelligent workflows.

AutoCraft can help with:

- Project scaffolding
- Code generation assistance
- File operations (sandboxed)
- Development workflow automation
- AI-powered diagnostics

---

## ✨ Features

### 🤖 AI Agent Engine
- Gemini-powered assistant (pluggable providers)
- Unified conversation + fact memory
- `AgentController` orchestration layer

### 🛠️ Tool System
- Modular tools with **ToolSandbox** allow-list
- Workspace path isolation
- Shell injection protection + blocked-command policy

### 🧩 Extensible Architecture
- `LLMProvider` abstraction (Gemini + Mock)
- Plugin registry foundation
- Custom tools and agents

---

## 📁 Project Structure

```text
AutoCraft/
├── src/
│   ├── agent/          # AgentController
│   ├── core/           # LLM client, unified memory
│   ├── llm/            # Provider abstraction
│   ├── security/       # ToolSandbox
│   ├── tools/          # file_ops (workspace-safe)
│   ├── cli.py
│   └── main.py
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Installation

```bash
git clone https://github.com/Hirunthakan432/AutoCraft.git
cd AutoCraft
pip install -r requirements.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

### Run

```bash
# Smoke-test agent
python -m src.main

# Interactive CLI
python -m src.cli

# Tests
pytest -v
```

---

## 🧠 Architecture

```text
User
 │
 ▼
AgentController
 ├── LLMProvider (Gemini / Mock)
 ├── AgentMemory (history + facts)
 ├── ToolSandbox → tools
 └── Plugins
```

---

## 🛣️ Roadmap

- [x] Gemini AI integration
- [x] Tool registry + sandbox
- [x] Unified agent memory
- [x] AgentController workflow
- [x] Multi-provider abstraction (Gemini + Mock)
- [ ] OpenAI / local model providers
- [ ] Multi-agent collaboration
- [ ] Web dashboard API
- [ ] Plugin marketplace
- [ ] Automated testing agent

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a pull request

---

## 📜 License

AutoCraft is released under the MIT License.
