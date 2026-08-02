"""Core agent controller for AutoCraft execution flow."""

from __future__ import annotations

from typing import Any, Optional

from src.core.memory import AgentMemory
from src.llm.provider import LLMProvider, MockProvider
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
        self.memory = memory or AgentMemory(
            system_instruction=system_instruction or DEFAULT_SYSTEM
        )
        if system_instruction and not self.memory.system_instruction:
            self.memory.system_instruction = system_instruction
        self.plugins = plugins
        self.sandbox = sandbox if sandbox is not None else create_default_sandbox()

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
        self.memory.clear_history()


def create_agent(
    *,
    use_mock: bool = False,
    system_instruction: Optional[str] = None,
) -> AgentController:
    """Factory used by CLI / main entry points."""
    if use_mock:
        llm: LLMProvider = MockProvider()
    else:
        from src.llm.provider import GeminiProvider

        llm = GeminiProvider()
    return AgentController(llm=llm, system_instruction=system_instruction)
