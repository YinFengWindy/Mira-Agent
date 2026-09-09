"""插件作用域运行时上下文：只暴露 manifest 声明的 capability，取代旧上帝对象。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.plugin_host.effects import Dispose, EffectScope
from agent.plugin_host.manifest import PluginManifest


class CapabilityNotGranted(AttributeError):
    """插件访问了 manifest 未声明的 capability。"""


class PluginRuntimeContext:
    """v2 插件在 setup(ctx) 中拿到的唯一句柄。

    通过属性访问已授予的 capability（ctx.tools / ctx.events / ctx.kv / ...）；
    未声明的能力访问时抛 CapabilityNotGranted，而不是拿到 None。
    """

    def __init__(
        self,
        *,
        plugin_id: str,
        plugin_dir: Path,
        manifest: PluginManifest,
        effects: EffectScope,
        capabilities: dict[str, Any],
    ) -> None:
        self.plugin_id = plugin_id
        self.plugin_dir = plugin_dir
        self.manifest = manifest
        self._effects = effects
        self._capabilities = capabilities

    @property
    def granted(self) -> tuple[str, ...]:
        """Returns granted capability names, for diagnostics."""
        return tuple(sorted(self._capabilities))

    def effect(self, label: str, dispose: Dispose) -> None:
        """登记插件自定义副作用（连接、文件监听等），卸载时逆序撤销。"""
        self._effects.add(f"custom:{label}", dispose)

    def __getattr__(self, name: str) -> Any:
        try:
            capabilities = object.__getattribute__(self, "_capabilities")
        except AttributeError as e:  # 构造未完成时保持原始 AttributeError 语义
            raise AttributeError(name) from e
        if name in capabilities:
            return capabilities[name]
        raise CapabilityNotGranted(
            f"插件 {self.plugin_id} 未声明 capability {name!r}；"
            f"已授予: {', '.join(self.granted) or '无'}"
        )
