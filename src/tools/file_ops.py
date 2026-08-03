import os
import shlex
import subprocess
from pathlib import Path
from typing import List


def _workspace_root() -> Path:
    """Resolve workspace at call time so cwd changes are respected."""
    return Path(os.getcwd()).resolve()


def _safe_path(path: str) -> Path:
    """Resolve path and ensure it stays inside the workspace."""
    root = _workspace_root()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise PermissionError(
            f"Path '{path}' is outside the allowed workspace ({root})."
        ) from e
    return candidate


def list_files(directory: str = ".") -> str:
    """Lists files and directories in the target directory (workspace only)."""
    try:
        target = _safe_path(directory)
        if not target.is_dir():
            return f"Error: '{directory}' is not a directory."
        items = sorted(os.listdir(target))
        return f"Contents of '{directory}':\n" + "\n".join(f"- {item}" for item in items)
    except PermissionError as e:
        return str(e)
    except Exception as e:
        return f"Error listing directory '{directory}': {e}"


def read_file(file_path: str) -> str:
    """Reads and returns the content of a file (workspace only)."""
    try:
        target = _safe_path(file_path)
        if not target.is_file():
            return f"Error: File '{file_path}' does not exist or is not a regular file."
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
        return f"--- Content of {file_path} ---\n{content}\n--- End of File ---"
    except PermissionError as e:
        return str(e)
    except Exception as e:
        return f"Error reading file '{file_path}': {e}"


def write_file(file_path: str, content: str) -> str:
    """Writes content to a file, creating directory paths if needed (workspace only)."""
    try:
        target = _safe_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} bytes to '{file_path}'."
    except PermissionError as e:
        return str(e)
    except Exception as e:
        return f"Error writing to file '{file_path}': {e}"


def run_command(command: str) -> str:
    """Runs a shell command safely within the current workspace (no shell injection)."""
    try:
        args: List[str] = shlex.split(command)
        if not args:
            return "Error: Empty command."

        result = subprocess.run(
            args,
            shell=False,
            cwd=str(_workspace_root()),
            capture_output=True,
            text=True,
            timeout=30,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        out = f"Exit Code: {result.returncode}\n"
        if stdout:
            out += f"STDOUT:\n{stdout}\n"
        if stderr:
            out += f"STDERR:\n{stderr}\n"
        return out
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out after 30 seconds."
    except Exception as e:
        return f"Error running command '{command}': {e}"
