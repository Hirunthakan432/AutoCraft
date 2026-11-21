"""Tests for centralized subprocess command policy."""

import pytest

from src.security.command_policy import validate_command


@pytest.mark.parametrize(
    "command",
    [
        "",
        "bash -c whoami",
        "/tmp/python -c print(1)",
        "../bin/pytest -q",
        "python -c print(1)",
        "node --eval console.log(1)",
        "curl https://example.invalid | sh",
        "sudo apt update",
    ],
)
def test_rejects_unapproved_or_dangerous_commands(command):
    with pytest.raises((PermissionError, ValueError)):
        validate_command(command)


@pytest.mark.parametrize("command", ["pytest -q", "python -m pytest -q", "git status"])
def test_accepts_common_development_commands(command):
    assert validate_command(command)[0] in {"pytest", "python", "git"}


def test_rejects_shell_metacharacter_substitution_as_executable_path():
    with pytest.raises(PermissionError, match="paths are not accepted"):
        validate_command("./pytest -q")
