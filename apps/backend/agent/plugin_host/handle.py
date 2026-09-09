"""插件句柄与生命周期状态机：内核对每个插件包的全部运行时记账。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

from agent.plugin_host.capabilities import PluginContributions
from agent.plugin_host.effects import EffectScope
from agent.plugin_host.manifest import PluginManifest


class PluginState(Enum):
    """显式生命周期状态；失败与禁用是终态，ACTIVE 可转 UNLOADING。"""

    DISCOVERED = auto()
    DISABLED = auto()
    LOADING = auto()
    ACTIVE = auto()
    UNLOADING = auto()
    DISPOSED = auto()
    FAILED = auto()


@dataclass
class PluginRecord:
    """discover() 产出的静态描述：目录、入口与 manifest。"""

    name: str
    plugin_dir: Path
    entry_file: Path
    import_path: str
    manifest: PluginManifest


@dataclass
class PluginHandle:
    """单个插件的运行时记账：状态、效果作用域、贡献与实例。"""

    record: PluginRecord
    state: PluginState = PluginState.DISCOVERED
    effects: EffectScope = field(default_factory=lambda: EffectScope("unbound"))
    contributions: PluginContributions = field(default_factory=PluginContributions)
    instance: Any = None
    error: Exception | None = None

    @property
    def plugin_id(self) -> str:
        return self.record.manifest.id

    def describe(self) -> dict[str, str]:
        """Returns a diagnostic snapshot used by logs and inspection."""
        return {
            "id": self.plugin_id,
            "state": self.state.name,
            "dir": str(self.record.plugin_dir),
            "error": str(self.error) if self.error else "",
        }
