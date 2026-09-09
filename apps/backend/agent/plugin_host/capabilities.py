"""按产品扩展点划分的 capability 实现：插件只拿到 manifest 声明的窄接口。"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from agent.plugin_host.effects import EffectScope

if TYPE_CHECKING:
    from agent.core.proactive_turn.gates import ProactiveGate
    from agent.tool_hooks.base import ToolHook
    from infra.channels.contract import Channel

logger = logging.getLogger(__name__)

# Shiori 定义的 7 个 phase 槽位；顺序与 AgentLoop 接线一致
PHASE_SLOTS = (
    "before_turn",
    "before_reasoning",
    "prompt_render",
    "before_step",
    "after_step",
    "after_reasoning",
    "after_turn",
)


class PluginContributions:
    """单个插件贡献的运行时对象集合；随插件卸载整体废弃。"""

    def __init__(self) -> None:
        self.phase_modules: dict[str, list[object]] = {slot: [] for slot in PHASE_SLOTS}
        self.tool_hooks: list[ToolHook] = []
        self.proactive_gates: list[ProactiveGate] = []
        self.channels: list[Channel] = []
        self.tool_names: list[str] = []


class ToolsCapability:
    """注册插件工具到 ToolRegistry；卸载时通过 effect 反注册。"""

    def __init__(
        self,
        registry: Any,
        effects: EffectScope,
        contributions: PluginContributions,
        plugin_id: str,
    ) -> None:
        self._registry = registry
        self._effects = effects
        self._contributions = contributions
        self._plugin_id = plugin_id

    def register(
        self,
        tool: Any,
        *,
        risk: str = "read-write",
        always_on: bool = False,
        search_hint: str | None = None,
    ) -> None:
        if self._registry is None:
            raise RuntimeError(f"插件 {self._plugin_id} 请求 tools 能力，但宿主未提供 ToolRegistry")
        name = str(tool.name)
        self._registry.register(
            tool,
            risk=risk,
            always_on=always_on,
            search_hint=search_hint,
            source_type="plugin",
            source_name=self._plugin_id,
        )
        self._contributions.tool_names.append(name)
        self._effects.add(f"tool:{name}", lambda: self._unregister(name))

    def _unregister(self, name: str) -> None:
        if self._registry is not None:
            self._registry.unregister(name)
        if name in self._contributions.tool_names:
            self._contributions.tool_names.remove(name)


class LifecycleCapability:
    """向 Shiori 定义的 phase 槽位贡献模块；槽位顺序语义仍由核心拥有。"""

    def __init__(self, contributions: PluginContributions, effects: EffectScope) -> None:
        self._contributions = contributions
        self._effects = effects

    def contribute(self, slot: str, modules: list[object]) -> None:
        if slot not in PHASE_SLOTS:
            raise ValueError(f"未知 phase 槽位: {slot}")
        target = self._contributions.phase_modules[slot]
        target.extend(modules)

        def remove_contributed() -> None:
            for module in modules:
                if module in target:
                    target.remove(module)

        self._effects.add(f"phase:{slot}:{len(modules)}", remove_contributed)


class ToolHooksCapability:
    """贡献工具执行前置 hook（ToolExecutor pre_hook 链）。"""

    def __init__(self, contributions: PluginContributions, effects: EffectScope) -> None:
        self._contributions = contributions
        self._effects = effects

    def add(self, hook: "ToolHook") -> None:
        self._contributions.tool_hooks.append(hook)
        self._effects.add(
            f"tool_hook:{getattr(hook, 'name', hook)}",
            lambda: self._discard(hook),
        )

    def _discard(self, hook: "ToolHook") -> None:
        if hook in self._contributions.tool_hooks:
            self._contributions.tool_hooks.remove(hook)


class ProactiveGatesCapability:
    """贡献参与主动 tick 准入的 gate；不允许直接投递消息。"""

    def __init__(self, contributions: PluginContributions, effects: EffectScope) -> None:
        self._contributions = contributions
        self._effects = effects

    def add(self, gate: "ProactiveGate") -> None:
        self._contributions.proactive_gates.append(gate)
        self._effects.add(
            f"proactive_gate:{getattr(gate, 'name', gate)}",
            lambda: self._discard(gate),
        )

    def _discard(self, gate: "ProactiveGate") -> None:
        if gate in self._contributions.proactive_gates:
            self._contributions.proactive_gates.remove(gate)


class ChannelsCapability:
    """贡献渠道 adapter；渠道宿主接管其生命周期。"""

    def __init__(self, contributions: PluginContributions, effects: EffectScope) -> None:
        self._contributions = contributions
        self._effects = effects

    def add(self, channel: "Channel") -> None:
        self._contributions.channels.append(channel)
        self._effects.add(
            f"channel:{getattr(channel, 'name', channel)}",
            lambda: self._discard(channel),
        )

    def _discard(self, channel: "Channel") -> None:
        if channel in self._contributions.channels:
            self._contributions.channels.remove(channel)


class BackgroundCapability:
    """启动可取消后台任务；插件卸载时任务被取消并等待退出。"""

    def __init__(self, effects: EffectScope, plugin_id: str) -> None:
        self._effects = effects
        self._plugin_id = plugin_id

    def spawn(self, coro: Any, *, name: str) -> asyncio.Task[Any]:
        task: asyncio.Task[Any] = asyncio.create_task(
            coro, name=f"plugin:{self._plugin_id}:{name}"
        )
        self._effects.add(f"background:{name}", lambda: self._cancel(task))
        return task

    @staticmethod
    async def _cancel(task: asyncio.Task[Any]) -> None:
        if task.done():
            return
        _ = task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001 - 卸载路径只收敛不传播
            pass
