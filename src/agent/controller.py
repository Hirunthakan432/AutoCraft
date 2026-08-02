"""Core agent controller for AutoCraft execution flow."""

from typing import Any

from src.security.sandbox import ToolSandbox, create_default_sandbox


class AgentController:
    def __init__(self, llm=None, memory=None, plugins=None, sandbox: ToolSandbox | None = None):
        self.llm = llm
        self.memory = memory
        self.plugins = plugins
        self.sandbox = sandbox if sandbox is not None else create_default_sandbox()

    def run_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a tool through the sandbox."""
        return self.sandbox.execute(name, *args, **kwargs)

    def run(self, task: str) -> Any:
        if self.memory:
            self.memory.remember("tasks", task)

        if self.llm:
            # Prefer chat-style API if available
            if hasattr(self.llm, "generate_chat_response"):
                return self.llm.generate_chat_response(
                    history=[{"role": "user", "content": task}],
                )
            if hasattr(self.llm, "generate"):
                return self.llm.generate(task)

        return {"status": "completed", "task": task}
