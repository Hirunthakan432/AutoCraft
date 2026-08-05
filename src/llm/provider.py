"""LLM provider abstraction for multi-model support."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Iterator, List, Optional

import requests


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

    def stream_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> Iterator[str]:
        """Yield response chunks for streaming UIs.

        Default implementation yields the full generate_chat_response result
        as a single chunk so non-streaming backends still work.
        """
        yield self.generate_chat_response(history, system_instruction)


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

    def stream_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> Iterator[str]:
        """Yield the mock reply in small word-sized chunks."""
        full = self.generate_chat_response(history, system_instruction)
        self.calls.append({"type": "stream", "full": full})
        parts = full.split(" ")
        for i, part in enumerate(parts):
            chunk = part if i == len(parts) - 1 else part + " "
            yield chunk


class GeminiProvider(LLMProvider):
    """Adapter around the existing GeminiClient."""

    def __init__(self, client=None, sandbox=None, **client_kwargs):
        if client is None:
            from src.core.llm import GeminiClient

            if sandbox is not None:
                client_kwargs = {**client_kwargs, "sandbox": sandbox}
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

    def stream_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> Iterator[str]:
        """Stream via GeminiClient when available; otherwise single-chunk fallback."""
        stream_fn = getattr(self.client, "stream_chat_response", None)
        if callable(stream_fn):
            yield from stream_fn(
                history=history,
                system_instruction=system_instruction,
            )
        else:
            yield self.generate_chat_response(history, system_instruction)


def _history_to_openai_messages(
    history: List[dict],
    system_instruction: Optional[str] = None,
) -> List[dict]:
    messages: List[dict] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    for msg in history:
        role = msg.get("role", "user")
        if role == "model":
            role = "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})
    return messages


class OpenAIProvider(LLMProvider):
    """OpenAI Chat Completions API (also works with compatible proxies)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is missing from environment variables.")
        # Prefer explicit arg, then env, then default
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _chat(self, messages: List[dict]) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "messages": messages}
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def generate(self, prompt: str) -> str:
        return self._chat([{"role": "user", "content": prompt}])

    def generate_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> str:
        messages = _history_to_openai_messages(history, system_instruction)
        return self._chat(messages)

    def stream_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> Iterator[str]:
        """Stream tokens from the OpenAI-compatible chat completions API."""
        messages = _history_to_openai_messages(history, system_instruction)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "messages": messages, "stream": True}
        with requests.post(
            url, headers=headers, json=payload, timeout=self.timeout, stream=True
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        import json as _json

                        obj = _json.loads(data)
                        delta = obj["choices"][0].get("delta") or {}
                        content = delta.get("content")
                        if content:
                            yield content
                    except (KeyError, ValueError, IndexError):
                        continue


class LocalProvider(LLMProvider):
    """Local OpenAI-compatible server (e.g. Ollama at localhost:11434)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
    ):
        self.base_url = (
            base_url
            or os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
        ).rstrip("/")
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "llama3.2")
        self.timeout = timeout
        self.api_key = os.getenv("LOCAL_LLM_API_KEY", "ollama")

    def _chat(self, messages: List[dict]) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "messages": messages, "stream": False}
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def generate(self, prompt: str) -> str:
        return self._chat([{"role": "user", "content": prompt}])

    def generate_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> str:
        messages = _history_to_openai_messages(history, system_instruction)
        return self._chat(messages)

    def stream_chat_response(
        self,
        history: List[dict],
        system_instruction: Optional[str] = None,
    ) -> Iterator[str]:
        """Stream tokens from a local OpenAI-compatible server (e.g. Ollama)."""
        messages = _history_to_openai_messages(history, system_instruction)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "messages": messages, "stream": True}
        with requests.post(
            url, headers=headers, json=payload, timeout=self.timeout, stream=True
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        import json as _json

                        obj = _json.loads(data)
                        delta = obj["choices"][0].get("delta") or {}
                        content = delta.get("content")
                        if content:
                            yield content
                    except (KeyError, ValueError, IndexError):
                        continue


def create_provider(
    name: Optional[str] = None,
    *,
    sandbox=None,
) -> LLMProvider:
    """Build a provider from name or AUTOCRAFT_PROVIDER env (default: gemini)."""
    key = (name or os.getenv("AUTOCRAFT_PROVIDER", "gemini")).strip().lower()
    if key in ("mock", "test"):
        return MockProvider()
    if key in ("openai", "gpt"):
        return OpenAIProvider()
    if key in ("local", "ollama"):
        return LocalProvider()
    if key in ("gemini", "google"):
        return GeminiProvider(sandbox=sandbox)
    raise ValueError(
        f"Unknown provider '{key}'. Use: gemini | openai | local | mock"
    )
