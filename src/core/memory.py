"""Unified memory for AutoCraft agents.

Combines short-term conversation history with longer-term key/value facts.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class AgentMemory:
    """Conversation history + persistent fact store for a single agent session."""

    def __init__(self, system_instruction: Optional[str] = None):
        self.system_instruction = system_instruction
        self.history: List[Dict[str, str]] = []
        self.facts: Dict[str, List[str]] = {}

    # --- conversation -----------------------------------------------------

    def add_user_message(self, content: str) -> None:
        self.history.append({"role": "user", "content": content})

    def add_agent_message(self, content: str) -> None:
        self.history.append({"role": "model", "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        return list(self.history)

    def clear_history(self) -> None:
        self.history.clear()

    # --- long-term facts --------------------------------------------------

    def remember(self, key: str, value: str) -> None:
        self.facts.setdefault(key, []).append(value)

    def recall(self, key: str) -> List[str]:
        return list(self.facts.get(key, []))

    def clear_facts(self) -> None:
        self.facts.clear()

    def clear(self) -> None:
        """Clear both conversation history and facts."""
        self.clear_history()
        self.clear_facts()


# Backwards-compatible alias used by older CLI imports
ConversationMemory = AgentMemory
