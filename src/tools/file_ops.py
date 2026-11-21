"""Workspace-scoped file tools and policy-checked command execution."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from src.security.command_policy import sanitized_environment, validate_command


def _workspace_root() -> Path:
    """Resolve workspace at call time so cwd changes are respected."""
    return Path(os.getcwd()).resolve()


def _safe_path(path: str) -> Path:
    """Resolve path and ensure it stays inside the workspace."""
    root = _workspace_root()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError(
            f"Path '{path}' is outside the allowed workspace ({root})."
        ) from exc
    return candidate


def list_files(directory: str = ".") -> str:
    """Lists files and directories in the target directory (workspace only)."""
    try:
        target = _safe_path(directory)
        if not target.is_dir():
            return f"Error: '{directory}' is not a directory."
        items = sorted(os.listdir(target))
        return f"Contents of '{directory}':\n" + "\n".join(f"- {item}" for item in items)
    except PermissionError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error listing directory '{directory}': {exc}"


def read_file(file_path: str) -> str:
    """Reads and returns the content of a file (workspace only)."""
    try:
        target = _safe_path(file_path)
        if not target.is_file():
            return f"Error: File '{file_path}' does not exist or is not a regular file."
        with target.open("r", encoding="utf-8") as file:
            content = file.read()
        return f"--- Content of {file_path} ---\n{content}\n--- End of File ---"
    except PermissionError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error reading file '{file_path}': {exc}"


def write_file(file_path: str, content: str) -> str:
    """Writes content to a file, creating directory paths if needed (workspace only)."""
    try:
        target = _safe_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as file:
            file.write(content)
        return f"Successfully wrote {len(content)} bytes to '{file_path}'."
    except PermissionError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error writing to file '{file_path}': {exc}"


def run_command(command: str) -> str:
    """Run an allow-listed argv command in the workspace without invoking a shell.

    The process receives a filtered environment and a hard timeout. This remains
    a policy layer, not a substitute for OS/container isolation.
    """
    try:
        args = validate_command(command)
        result = subprocess.run(
            args,
            shell=False,
            cwd=str(_workspace_root()),
            env=sanitized_environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout.strip():
            output += f"STDOUT:\n{result.stdout.strip()}\n"
        if result.stderr.strip():
            output += f"STDERR:\n{result.stderr.strip()}\n"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out after 30 seconds."
    except (PermissionError, ValueError) as exc:
        return f"Sandbox denied: {exc}"
    except Exception as exc:
        return f"Error running command '{command}': {exc}"
