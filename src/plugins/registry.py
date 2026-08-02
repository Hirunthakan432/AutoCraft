"""Plugin registry for extending AutoCraft agents."""

from typing import Callable, Dict


class PluginRegistry:
    def __init__(self) -> None:
        self.plugins: Dict[str, Callable] = {}

    def register(self, name: str, plugin: Callable) -> None:
        self.plugins[name] = plugin

    def get(self, name: str) -> Callable | None:
        return self.plugins.get(name)

    def list_plugins(self) -> list[str]:
        return list(self.plugins.keys())
