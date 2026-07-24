import os
import subprocess
from typing import Dict, Any

def list_files(directory: str = ".") -> str:
    """Lists files and directories in the target directory."""
    try:
        items = os.listdir(directory)
        return f"Contents of '{directory}':\n" + "\n".join(f"- {item}" for item in items)
    except Exception as e:
        return f"Error listing directory '{directory}': {e}"

def read_file(file_path: str) -> str:
    """Reads and returns the content of a file."""
    try:
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist."
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"--- Content of {file_path} ---\n{content}\n--- End of File ---"
    except Exception as e:
        return f"Error reading file '{file_path}': {e}"

def write_file(file_path: str, content: str) -> str:
    """Writes content to a file, creating directory paths if needed."""
    try:
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} bytes to '{file_path}'."
    except Exception as e:
        return f"Error writing to file '{file_path}': {e}"

def run_command(command: str) -> str:
    """Runs a shell command safely within the current workspace."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
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