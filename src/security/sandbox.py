"""Basic tool execution safety layer for AutoCraft."""

from typing import Any, Callable


class ToolSandbox:
    """Simple allow-list based tool executor."""

    def __init__(self) -> None:
        self.allowed_tools: dict[str, Callable] = {}

    def register(self, name: str, tool: Callable) -> None:
        self.allowed_tools[name] = tool

    def execute(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if name not in self.allowed_tools:
            raise PermissionError(f"Tool '{name}' is not allowed")
        return self.allowed_tools[name](*args, **kwargs)

    def list_allowed(self) -> list[str]:
        return list(self.allowed_tools.keys())
