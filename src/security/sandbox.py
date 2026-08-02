"""Basic tool execution safety layer for AutoCraft."""

from typing import Callable, Any


class ToolSandbox:
    def __init__(self):
        self.allowed_tools: dict[str, Callable] = {}

    def register(self, name: str, tool: Callable) -> None:
        self.allowed_tools[name] = tool

    def execute(self, name: str, *args, **kwargs) -> Any:
        if name not in self.allowed_tools:
            raise PermissionError(f"Tool '{name}' is not allowed")

        return self.allowed_tools[name](*args, **kwargs)
