"""Core agent controller for AutoCraft execution flow."""

from __future__ import annotations

from typing import Any, Optional

from src.core.memory import AgentMemory
from src.llm.provider import LLMProvider, MockProvider, create_provider
from src.security.sandbox import ToolSandbox, create_default_sandbox

DEFAULT_SYSTEM = (
    "You are AutoCraft, an intelligent AI software architecture & automation agent. "
    "You provide concise, high-quality, and structured technical responses."
)


class AgentController:
    """Orchestrates LLM, memory, tools (via sandbox), and plugins."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        memory: Optional[AgentMemory] = None,
        plugins=None,
        sandbox: Optional[ToolSandbox] = None,
        system_instruction: Optional[str] = None,
    ):
        self.llm = llm
        self.sandbox = sandbox if sandbox is not None else create_default_sandbox()
        self.plugins = plugins

        if memory is not None:
            self.memory = memory
            # Explicit system_instruction always wins when provided
            if system_instruction is not None:
                self.memory.system_instruction = system_instruction
            elif not self.memory.system_instruction:
                self.memory.system_instruction = DEFAULT_SYSTEM
        else:
            self.memory = AgentMemory(
                system_instruction=system_instruction or DEFAULT_SYSTEM
            )

    def run_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a tool through the sandbox."""
        return self.sandbox.execute(name, *args, **kwargs)

    def run(self, task: str) -> Any:
        """Run a single task end-to-end: remember, call LLM, store reply."""
        self.memory.remember("tasks", task)
        self.memory.add_user_message(task)

        if self.llm is None:
            result = {"status": "completed", "task": task, "response": None}
            self.memory.add_agent_message(str(result))
            return result

        response = self.llm.generate_chat_response(
            history=self.memory.get_history(),
            system_instruction=self.memory.system_instruction,
        )
        self.memory.add_agent_message(response)
        self.memory.remember("responses", response)
        return response

    def chat(self, message: str) -> str:
        """Alias for interactive multi-turn use."""
        result = self.run(message)
        return result if isinstance(result, str) else str(result)

    def clear_session(self) -> None:
        """Clear conversation history and long-term facts for this session."""
        self.memory.clear()


def create_agent(
    *,
    use_mock: bool = False,
    provider: Optional[str] = None,
    system_instruction: Optional[str] = None,
    sandbox: Optional[ToolSandbox] = None,
) -> AgentController:
    """Factory used by CLI / main entry points.

    Priority: use_mock → explicit provider name → AUTOCRAFT_PROVIDER env → gemini.
    Gemini shares the same ToolSandbox instance as the controller.
    """
    box = sandbox if sandbox is not None else create_default_sandbox()
    if use_mock:
        llm: LLMProvider = MockProvider()
    else:
        llm = create_provider(provider, sandbox=box)
    return AgentController(
        llm=llm,
        system_instruction=system_instruction,
        sandbox=box,
    )
