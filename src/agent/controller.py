"""Core agent controller for AutoCraft execution flow."""

from typing import Any


class AgentController:
    def __init__(self, llm=None, memory=None, plugins=None):
        self.llm = llm
        self.memory = memory
        self.plugins = plugins

    def run(self, task: str) -> Any:
        if self.memory:
            self.memory.remember("tasks", task)

        if self.llm:
            return self.llm.generate(task)

        return {"status": "completed", "task": task}
