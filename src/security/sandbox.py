"""Tool execution safety layer for AutoCraft.

Provides an allow-list based sandbox that:
- Only permits explicitly registered tools
- Blocks dangerous shell commands
- Can wrap callables for use with the Gemini SDK
"""

from __future__ import annotations

import functools
import re
from typing import Any, Callable, Iterable

# Patterns that must never reach subprocess (case-insensitive).
# Matched against the full command string before shlex splitting.
BLOCKED_COMMAND_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\brm\s+(-[a-zA-Z]*f|.*\s-rf|--force)",  # rm -rf / force deletes
        r"\bsudo\b",
        r"\bchmod\b",
        r"\bchown\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r">\s*/dev/",
        r"\bcurl\b.*\|\s*(ba)?sh",
        r"\bwget\b.*\|\s*(ba)?sh",
        r"\beval\b",
        r"\bexec\b\s",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bpoweroff\b",
        r"\bkill\s+-9\b",
        r"\bpkill\b",
        r"\b:(){:|:&};:",  # fork bomb
    )
)


class ToolSandbox:
    """Allow-list tool executor with optional command policy for shell tools."""

    def __init__(
        self,
        *,
        blocked_patterns: Iterable[re.Pattern[str]] | None = None,
    ) -> None:
        self.allowed_tools: dict[str, Callable[..., Any]] = {}
        self.blocked_patterns = (
            tuple(blocked_patterns) if blocked_patterns is not None else BLOCKED_COMMAND_PATTERNS
        )

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

    def _check_command_policy(self, command: str) -> None:
        """Raise PermissionError if the command matches a blocked pattern."""
        for pattern in self.blocked_patterns:
            if pattern.search(command):
                raise PermissionError(
                    f"Command blocked by sandbox policy: matches '{pattern.pattern}'"
                )

    def execute(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Run a registered tool. Applies command policy for run_command."""
        if name not in self.allowed_tools:
            raise PermissionError(f"Tool '{name}' is not allowed")

        if name == "run_command" and args:
            self._check_command_policy(str(args[0]))
        elif name == "run_command" and "command" in kwargs:
            self._check_command_policy(str(kwargs["command"]))

        return self.allowed_tools[name](*args, **kwargs)

    def wrap(self, name: str) -> Callable[..., Any]:
        """Return a Gemini-SDK-compatible wrapper that executes via this sandbox.

        The wrapper uses the *registered* name (not the underlying callable's
        __name__) so lambdas and renamed tools still expose a stable identity
        to the model.
        """
        if name not in self.allowed_tools:
            raise KeyError(f"Tool '{name}' is not registered")

        original = self.allowed_tools[name]

        @functools.wraps(original)
        def sandboxed_tool(*args: Any, **kwargs: Any) -> Any:
            try:
                return self.execute(name, *args, **kwargs)
            except PermissionError as e:
                return f"Sandbox denied: {e}"

        # Prefer the registration name over original.__name__ (e.g. <lambda>)
        sandboxed_tool.__name__ = name
        sandboxed_tool.__qualname__ = name
        if original.__doc__:
            sandboxed_tool.__doc__ = original.__doc__
        return sandboxed_tool

    def wrapped_tools(self, names: Iterable[str] | None = None) -> list[Callable[..., Any]]:
        """Return wrapped callables for the given names (or all registered tools)."""
        target = list(names) if names is not None else self.list_allowed()
        return [self.wrap(n) for n in target]


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
