"""Explicit plugin dependencies and generation-scoped exported APIs."""

from collections.abc import Callable
from typing import Any


class PluginDependencyError(RuntimeError):
    """A declared dependency is unavailable or forms a dependency cycle."""


class PluginDependencies:
    """Allows a plugin to read only the APIs of its declared dependencies."""

    def __init__(self, declared: tuple[str, ...], resolve: Callable[[str], Any]):
        self._declared = declared
        self._resolve = resolve

    def require(self, plugin_id: str) -> Any:
        """Returns the active dependency's public API within the same generation."""
        if plugin_id not in self._declared:
            raise PluginDependencyError(f"未声明插件依赖: {plugin_id}")
        return self._resolve(plugin_id)
