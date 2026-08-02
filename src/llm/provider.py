"""LLM provider abstraction for multi-model support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class LLMProvider(ABC):
    """Common interface every model backend must implement."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Single-shot generation from a plain prompt."""

    def generate_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> str:
        """Multi-turn chat. Default falls back to the last user message."""
        prompt = ""
        for msg in reversed(history):
            if msg.get("role") == "user":
                prompt = msg.get("content", "")
                break
        if system_instruction:
            prompt = f"{system_instruction}\n\n{prompt}"
        return self.generate(prompt)


class MockProvider(LLMProvider):
    """Deterministic provider for tests and offline development."""

    def __init__(self, prefix: str = "Mock response"):
        self.prefix = prefix
        self.calls: List[dict] = []

    def generate(self, prompt: str) -> str:
        self.calls.append({"type": "generate", "prompt": prompt})
        return f"{self.prefix}: {prompt}"

    def generate_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> str:
        self.calls.append(
            {
                "type": "chat",
                "history": list(history),
                "system_instruction": system_instruction,
            }
        )
        last_user = ""
        for msg in reversed(history):
            if msg.get("role") == "user":
                last_user = msg.get("content", "")
                break
        return f"{self.prefix}: {last_user}"


class GeminiProvider(LLMProvider):
    """Adapter around the existing GeminiClient."""

    def __init__(self, client=None, **client_kwargs):
        if client is None:
            from src.core.llm import GeminiClient

            client = GeminiClient(**client_kwargs)
        self.client = client

    def generate(self, prompt: str) -> str:
        return self.client.generate_chat_response(
            history=[{"role": "user", "content": prompt}],
        )

    def generate_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> str:
        return self.client.generate_chat_response(
            history=history,
            system_instruction=system_instruction,
        )
