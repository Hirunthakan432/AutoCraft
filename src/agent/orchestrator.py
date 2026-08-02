"""Multi-agent collaboration orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from src.agent.controller import AgentController, create_agent
from src.agent.roles import DEFAULT_PIPELINE, DEFAULT_ROLES, AgentRole
from src.llm.provider import LLMProvider, MockProvider


@dataclass
class StepResult:
    role: str
    input: str
    output: str


@dataclass
class CollaborationResult:
    goal: str
    steps: List[StepResult] = field(default_factory=list)
    final: str = ""

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [
                {"role": s.role, "input": s.input, "output": s.output} for s in self.steps
            ],
            "final": self.final,
        }


class MultiAgentOrchestrator:
    """Runs a sequential pipeline of role-specialized agents."""

    def __init__(
        self,
        *,
        roles: Optional[Dict[str, AgentRole]] = None,
        pipeline: Optional[Sequence[str]] = None,
        provider: Optional[str] = None,
        use_mock: bool = False,
        shared_llm: Optional[LLMProvider] = None,
    ):
        self.roles = dict(roles or DEFAULT_ROLES)
        self.pipeline = list(pipeline or DEFAULT_PIPELINE)
        self.provider = provider
        self.use_mock = use_mock
        self._agents: Dict[str, AgentController] = {}
        self._shared_llm = shared_llm

    def _agent_for(self, role_name: str) -> AgentController:
        if role_name not in self._agents:
            role = self.roles.get(role_name)
            if role is None:
                raise KeyError(f"Unknown role: {role_name}")
            if self._shared_llm is not None:
                agent = AgentController(
                    llm=self._shared_llm,
                    system_instruction=role.system_instruction,
                )
            else:
                agent = create_agent(
                    use_mock=self.use_mock,
                    provider=self.provider,
                    system_instruction=role.system_instruction,
                )
            self._agents[role_name] = agent
        return self._agents[role_name]

    def list_roles(self) -> List[dict]:
        return [
            {"name": r.name, "description": r.description}
            for r in self.roles.values()
        ]

    def run(
        self,
        goal: str,
        pipeline: Optional[Sequence[str]] = None,
    ) -> CollaborationResult:
        """Execute agents in order; each sees the prior outputs as context."""
        order = list(pipeline or self.pipeline)
        result = CollaborationResult(goal=goal)
        context_parts: List[str] = [f"User goal:\n{goal}"]

        for role_name in order:
            agent = self._agent_for(role_name)
            prompt = (
                "\n\n---\n".join(context_parts)
                + f"\n\n---\nYour role: {role_name}. Produce your contribution."
            )
            output = agent.chat(prompt)
            result.steps.append(StepResult(role=role_name, input=prompt, output=output))
            context_parts.append(f"{role_name.upper()} output:\n{output}")

        if result.steps:
            result.final = result.steps[-1].output
        return result

    def run_role(self, role_name: str, message: str) -> str:
        """Single-role invocation (no pipeline)."""
        return self._agent_for(role_name).chat(message)


def create_team(
    *,
    use_mock: bool = False,
    provider: Optional[str] = None,
    pipeline: Optional[Sequence[str]] = None,
) -> MultiAgentOrchestrator:
    """Factory for a standard planner → coder → reviewer team."""
    shared = MockProvider(prefix="Team") if use_mock else None
    return MultiAgentOrchestrator(
        use_mock=use_mock,
        provider=provider,
        pipeline=pipeline,
        shared_llm=shared,
    )
