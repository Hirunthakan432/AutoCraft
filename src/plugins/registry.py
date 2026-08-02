"""Plugin registry and in-repo marketplace catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PluginInfo:
    name: str
    description: str
    version: str = "0.1.0"
    author: str = "autocraft"
    tags: List[str] = field(default_factory=list)
    enabled: bool = False
    installed: bool = False


# Catalog of available plugins (marketplace listings).
# "install" registers a callable; real code can be swapped later.
MARKETPLACE_CATALOG: Dict[str, PluginInfo] = {
    "echo": PluginInfo(
        name="echo",
        description="Echo plugin for debugging agent pipelines",
        tags=["debug", "util"],
    ),
    "summarize": PluginInfo(
        name="summarize",
        description="Summarize long text into bullet points",
        tags=["nlp", "util"],
    ),
    "lint_hint": PluginInfo(
        name="lint_hint",
        description="Return basic style hints for a code snippet",
        tags=["code", "quality"],
    ),
}


def _builtin_echo(text: str = "") -> str:
    return f"echo: {text}"


def _builtin_summarize(text: str = "") -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "(empty)"
    bullets = lines[:8]
    return "Summary:\n" + "\n".join(f"- {b[:120]}" for b in bullets)


def _builtin_lint_hint(code: str = "") -> str:
    hints = []
    if "\t" in code:
        hints.append("Prefer spaces over tabs")
    if any(len(line) > 100 for line in code.splitlines()):
        hints.append("Some lines exceed 100 characters")
    if "print(" in code and "logging" not in code:
        hints.append("Consider logging instead of print in library code")
    return "OK" if not hints else "Hints:\n- " + "\n- ".join(hints)


BUILTIN_IMPLEMENTATIONS: Dict[str, Callable[..., Any]] = {
    "echo": _builtin_echo,
    "summarize": _builtin_summarize,
    "lint_hint": _builtin_lint_hint,
}


class PluginRegistry:
    """Installed plugins + marketplace catalog."""

    def __init__(self) -> None:
        self.plugins: Dict[str, Callable[..., Any]] = {}
        self.meta: Dict[str, PluginInfo] = {
            k: PluginInfo(**{**v.__dict__}) for k, v in MARKETPLACE_CATALOG.items()
        }

    def register(self, name: str, plugin: Callable[..., Any], *, enable: bool = True) -> None:
        self.plugins[name] = plugin
        info = self.meta.get(name) or PluginInfo(name=name, description="custom")
        info.installed = True
        info.enabled = enable
        self.meta[name] = info

    def install(self, name: str) -> PluginInfo:
        if name not in MARKETPLACE_CATALOG and name not in BUILTIN_IMPLEMENTATIONS:
            raise KeyError(f"Plugin '{name}' not found in marketplace")
        impl = BUILTIN_IMPLEMENTATIONS.get(name)
        if impl is None:
            raise KeyError(f"Plugin '{name}' has no implementation")
        self.register(name, impl, enable=True)
        return self.meta[name]

    def uninstall(self, name: str) -> None:
        self.plugins.pop(name, None)
        if name in self.meta:
            self.meta[name].installed = False
            self.meta[name].enabled = False

    def enable(self, name: str) -> None:
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not installed")
        self.meta[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self.meta:
            self.meta[name].enabled = False

    def get(self, name: str) -> Optional[Callable[..., Any]]:
        info = self.meta.get(name)
        if info and not info.enabled:
            return None
        return self.plugins.get(name)

    def run(self, name: str, *args: Any, **kwargs: Any) -> Any:
        fn = self.get(name)
        if fn is None:
            raise PermissionError(f"Plugin '{name}' is not available or disabled")
        return fn(*args, **kwargs)

    def list_plugins(self) -> List[str]:
        return [n for n, m in self.meta.items() if m.installed and m.enabled]

    def marketplace(self) -> List[dict]:
        return [
            {
                "name": m.name,
                "description": m.description,
                "version": m.version,
                "author": m.author,
                "tags": list(m.tags),
                "installed": m.installed,
                "enabled": m.enabled,
            }
            for m in self.meta.values()
        ]


def create_default_registry() -> PluginRegistry:
    reg = PluginRegistry()
    # Pre-install echo for a usable default
    reg.install("echo")
    return reg
