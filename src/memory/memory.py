"""Simple persistent memory interface for AutoCraft agents."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AgentMemory:
    """Stores agent context and learned information."""

    data: Dict[str, List[str]] = field(default_factory=dict)

    def remember(self, key: str, value: str) -> None:
        self.data.setdefault(key, []).append(value)

    def recall(self, key: str) -> List[str]:
        return self.data.get(key, [])

    def clear(self) -> None:
        self.data.clear()
