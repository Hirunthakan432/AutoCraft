"""Central command policy for AutoCraft's subprocess tool.

This is a command allow-list, not an OS/container security boundary. Run AutoCraft
with least-privilege OS permissions and use a dedicated container for untrusted code.
"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

DEFAULT_ALLOWED_COMMANDS = frozenset({
    "black",
    "git",
    "mypy",
    "node",
    "npm",
    "npx",
    "pytest",
    "python",
    "python3",
    "ruff",
    "uv",
})

BLOCKED_EXECUTABLES = frozenset({
    "bash", "cmd", "command", "fish", "powershell", "pwsh", "sh", "zsh",
})

BLOCKED_COMMAND_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brm\s+(-[a-zA-Z]*[rf]|.*\s-[rf]|--force|--recursive)",
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
        r"\b:(){:|:&};:",
        r"\bformat\b",
        r"\bfdisk\b",
        r"\bparted\b",
    )
)

_SECRET_ENV_MARKERS = (
    "API_KEY", "ACCESS_KEY", "TOKEN", "SECRET", "PASSWORD",
    "CREDENTIAL", "PRIVATE_KEY",
)
_ALWAYS_HIDDEN_ENV = frozenset({
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "SSH_AUTH_SOCK",
})


def allowed_commands() -> frozenset[str]:
    """Read the executable allow-list, allowing an explicit operator override."""
    configured = os.getenv("AUTOCRAFT_ALLOWED_COMMANDS", "").strip()
    if not configured:
        return DEFAULT_ALLOWED_COMMANDS
    return frozenset(
        item.strip().lower()
        for item in configured.split(",")
        if item.strip()
    )


def validate_command(command: str) -> list[str]:
    """Parse and validate a command before passing argv to subprocess.run."""
    if not isinstance(command, str) or not command.strip():
        raise ValueError("Command must be a non-empty string")

    for pattern in BLOCKED_COMMAND_PATTERNS:
        if pattern.search(command):
            raise PermissionError(
                f"Command blocked by sandbox policy: matches '{pattern.pattern}'"
            )

    try:
        args = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"Invalid command syntax: {exc}") from exc

    if not args:
        raise ValueError("Command must be a non-empty string")

    executable = Path(args[0]).name.lower()
    if executable in BLOCKED_EXECUTABLES:
        raise PermissionError(f"Executable '{executable}' is blocked by sandbox policy")
    if executable not in allowed_commands():
        raise PermissionError(
            f"Executable '{executable}' is not in AUTOCRAFT_ALLOWED_COMMANDS"
        )

    # Do not permit inline interpreter evaluation. Running project files and
    # pytest remains supported; shell interpreters are blocked above.
    if executable in {"python", "python3"} and any(
        arg == "-c" or arg.startswith("-c") for arg in args[1:]
    ):
        raise PermissionError("Inline Python execution is blocked by sandbox policy")
    if executable in {"node", "npm", "npx"} and any(
        arg in {"-e", "--eval"} or arg.startswith("--eval=") for arg in args[1:]
    ):
        raise PermissionError("Inline JavaScript execution is blocked by sandbox policy")

    return args


def sanitized_environment() -> dict[str, str]:
    """Copy the process environment without common credential-bearing values."""
    clean: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if upper in _ALWAYS_HIDDEN_ENV:
            continue
        if any(marker in upper for marker in _SECRET_ENV_MARKERS):
            continue
        clean[key] = value
    return clean
