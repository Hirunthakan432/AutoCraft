"""Tool execution safety layer for AutoCraft.

Provides an explicit tool allow-list and applies the shared command policy to
run_command. This is not an OS-level sandbox; untrusted code should run inside
a dedicated, least-privilege container.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Iterable

from src.security.command_policy import validate_command


class ToolSandbox:
    """Allow-list tool executor with command policy for shell tools."""

    def __init__(self) -> None:
        self.allowed_tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, tool: Callable[..., Any]) -> None:
        """Register a tool under an explicit name."""
        if not name or not callable(tool):
            raise ValueError("Tool name and callable are required")
        self.allowed_tools[name] = tool

    def register_many(self, tools: dict[str, Callable[..., Any]]) -> None:
        for name, tool in tools.items():
            self.register(name, tool)

    def unregister(self, name: str) -> None:
        self.allowed_tools.pop(name, None)

    def is_allowed(self, name: str) -> bool:
        return name in self.allowed_tools

    def list_allowed(self) -> list[str]:
        return sorted(self.allowed_tools.keys())

    def execute(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Run a registered tool; validate commands before invoking run_command."""
        if name not in self.allowed_tools:
            raise PermissionError(f"Tool '{name}' is not allowed")

        if name == "run_command":
            command = args[0] if args else kwargs.get("command")
            validate_command(command)

        return self.allowed_tools[name](*args, **kwargs)

    def wrap(self, name: str) -> Callable[..., Any]:
        """Return a Gemini-SDK-compatible wrapper that executes via this sandbox."""
        if name not in self.allowed_tools:
            raise KeyError(f"Tool '{name}' is not registered")

        original = self.allowed_tools[name]

        @functools.wraps(original)
        def sandboxed_tool(*args: Any, **kwargs: Any) -> Any:
            try:
                return self.execute(name, *args, **kwargs)
            except PermissionError as exc:
                return f"Sandbox denied: {exc}"

        sandboxed_tool.__name__ = name
        sandboxed_tool.__qualname__ = name
        if original.__doc__:
            sandboxed_tool.__doc__ = original.__doc__
        return sandboxed_tool

    def wrapped_tools(self, names: Iterable[str] | None = None) -> list[Callable[..., Any]]:
        """Return wrapped callables for the given names (or all registered tools)."""
        target = list(names) if names is not None else self.list_allowed()
        return [self.wrap(name) for name in target]


def create_default_sandbox() -> ToolSandbox:
    """Factory: sandbox pre-loaded with the standard file/command tools."""
    from src.tools.file_ops import list_files, read_file, write_file, run_command

    sandbox = ToolSandbox()
    sandbox.register_many(
        {
            "list_files": list_files,
            "read_file": read_file,
            "write_file": write_file,
            "run_command": run_command,
        }
    )
    return sandbox
