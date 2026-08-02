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
- File operations
- Development workflow automation
- AI-powered diagnostics

The goal is to create a developer-focused AI assistant that can understand tasks and execute structured workflows.

---

## ✨ Features

### 🤖 AI Agent Engine
- Gemini-powered AI assistant
- Natural language task processing
- Intelligent development workflows

### 🛠️ Tool System
- Modular tool registry
- File reading and writing support
- Command execution framework

### 🧩 Extensible Architecture
- Add custom AI providers
- Add new tools and plugins
- Build specialized agents

---

## 📁 Project Structure

```text
AutoCraft/
├── src/
│   ├── core/
│   │   └── llm.py
│   ├── tools/
│   └── main.py
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/Hirunthakan432/AutoCraft.git
cd AutoCraft
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

### 4. Run AutoCraft

```bash
python -m src.main
```

---

## 🧠 Architecture

```text
User
 │
 ▼
AutoCraft Agent
 │
 ├── LLM Provider
 │
 ├── Tool Registry
 │
 └── Automation Workflow Engine
```

---

## 🛣️ Roadmap

- [x] Gemini AI integration
- [x] Tool registry system
- [x] Agent startup workflow
- [ ] Multi-agent collaboration
- [ ] Web dashboard
- [ ] Plugin marketplace
- [ ] Long-term memory system
- [ ] Automated testing agent

---

## 🤝 Contributing

Contributions, ideas, and improvements are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a pull request

---

## 📜 License

AutoCraft is released under the MIT License.
