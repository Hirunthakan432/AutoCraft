"""LLM provider abstraction for future multi-model support."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response from a language model."""
        raise NotImplementedError


class MockProvider(LLMProvider):
    """Development provider used for testing agent workflows."""

    def generate(self, prompt: str) -> str:
        return f"Mock response: {prompt}"
