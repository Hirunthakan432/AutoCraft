"""Automated testing agent — proposes and runs tests via the sandbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.agent.controller import AgentController, create_agent
from src.security.sandbox import ToolSandbox, create_default_sandbox

TESTER_SYSTEM = (
    "You are the Testing agent in AutoCraft. "
    "Given a goal or code change description, propose a minimal pytest plan: "
    "list test cases, suggested file names, and exact pytest command. "
    "Be concise."
)


@dataclass
class TestRunResult:
    plan: str
    command: str
    command_output: str
    passed: Optional[bool] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "plan": self.plan,
            "command": self.command,
            "command_output": self.command_output,
            "passed": self.passed,
            "notes": list(self.notes),
        }


class TestingAgent:  # noqa: N801 - name is intentional product term
    """Plans tests with an LLM and optionally executes pytest in the sandbox."""

    __test__ = False  # prevent pytest from collecting this as a test class

    def __init__(
        self,
        *,
        agent: Optional[AgentController] = None,
        sandbox: Optional[ToolSandbox] = None,
        use_mock: bool = False,
        provider: Optional[str] = None,
    ):
        self.agent = agent or create_agent(
            use_mock=use_mock,
            provider=provider,
            system_instruction=TESTER_SYSTEM,
        )
        self.sandbox = sandbox if sandbox is not None else create_default_sandbox()

    def plan(self, goal: str) -> str:
        return self.agent.chat(
            f"Propose pytest coverage for this goal:\n{goal}\n"
            "End with a single line: COMMAND: pytest -q"
        )

    def run_pytest(self, args: str = "-q") -> str:
        cmd = f"pytest {args}".strip()
        return str(self.sandbox.execute("run_command", cmd))

    def run(self, goal: str, *, execute: bool = True) -> TestRunResult:
        plan = self.plan(goal)
        command = "pytest -q"
        for line in plan.splitlines():
            if line.strip().upper().startswith("COMMAND:"):
                command = line.split(":", 1)[1].strip() or command
                break

        notes: List[str] = []
        output = ""
        passed: Optional[bool] = None

        if execute:
            if not command.strip().startswith("pytest"):
                notes.append("Refused non-pytest command; falling back to pytest -q")
                command = "pytest -q"
            try:
                args = command.replace("pytest", "", 1).strip() or "-q"
                output = self.run_pytest(args)
                passed = None
                for part in output.splitlines():
                    if part.startswith("Exit Code:"):
                        try:
                            passed = int(part.split(":", 1)[1].strip()) == 0
                        except ValueError:
                            passed = False
            except Exception as e:
                output = str(e)
                notes.append("Execution error")
                passed = False
        else:
            notes.append("execute=False; skipped pytest")

        return TestRunResult(
            plan=plan,
            command=command,
            command_output=output,
            passed=passed,
            notes=notes,
        )
