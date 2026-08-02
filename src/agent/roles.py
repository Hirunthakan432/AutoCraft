"""Built-in agent roles for multi-agent collaboration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AgentRole:
    name: str
    description: str
    system_instruction: str


PLANNER = AgentRole(
    name="planner",
    description="Breaks goals into ordered steps",
    system_instruction=(
        "You are the Planner agent in AutoCraft. "
        "Given a user goal, produce a short, numbered plan of concrete steps. "
        "Do not implement code. Be concise and actionable."
    ),
)

CODER = AgentRole(
    name="coder",
    description="Implements solutions from a plan",
    system_instruction=(
        "You are the Coder agent in AutoCraft. "
        "Given a plan and context, produce focused implementation guidance or code. "
        "Prefer clarity and correctness over length."
    ),
)

REVIEWER = AgentRole(
    name="reviewer",
    description="Reviews plans and implementations for risks",
    system_instruction=(
        "You are the Reviewer agent in AutoCraft. "
        "Critique the plan and implementation for bugs, security issues, and missing tests. "
        "List findings briefly; suggest fixes when useful."
    ),
)

RESEARCHER = AgentRole(
    name="researcher",
    description="Gathers context and constraints",
    system_instruction=(
        "You are the Researcher agent in AutoCraft. "
        "Summarize relevant constraints, assumptions, and open questions for the goal. "
        "Do not write full implementations."
    ),
)

TESTER = AgentRole(
    name="tester",
    description="Proposes and validates automated tests",
    system_instruction=(
        "You are the Testing agent in AutoCraft. "
        "Propose minimal pytest cases and a COMMAND: pytest … line. "
        "Focus on regressions and edge cases."
    ),
)

DEFAULT_ROLES: Dict[str, AgentRole] = {
    PLANNER.name: PLANNER,
    CODER.name: CODER,
    REVIEWER.name: REVIEWER,
    RESEARCHER.name: RESEARCHER,
    TESTER.name: TESTER,
}

# Default collaboration pipeline order
DEFAULT_PIPELINE = ("planner", "coder", "reviewer")
FULL_PIPELINE = ("planner", "coder", "tester", "reviewer")
