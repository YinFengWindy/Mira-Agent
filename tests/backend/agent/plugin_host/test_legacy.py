"""legacy 适配器行为：旧 Plugin ABC 插件零改动跑在内核上，卸载全量回收。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.plugin_host import HostServices, PluginKernel
from bus.event_bus import EventBus
from agent.tools.registry import ToolRegistry

from tests.backend.agent.plugin_host.conftest import (
    before_turn_ctx,
    make_kernel,
    stage_plugin_fixture,
)


@pytest.mark.asyncio
async def test_legacy_decorator_handler_fires_and_unbinds_on_unload(tmp_path: Path):
    stage_plugin_fixture("hello", tmp_path)
    bus = EventBus()
    kernel = make_kernel([tmp_path], event_bus=bus)
    await kernel.load_all()
    assert kernel.loaded_count == 1

    result = await bus.emit(before_turn_ctx())
    assert result.extra_metadata.get("hello_touched") is True

    _ = await kernel.unload("hello")
    result_after = await bus.emit(before_turn_ctx())
    assert "hello_touched" not in result_after.extra_metadata


@pytest.mark.asyncio
async def test_legacy_tool_hook_name_matches_v2_convention(tmp_path: Path):
    """legacy 适配器与 v2 ToolHooksCapability.add_handler 必须共用同一份命名逻辑
    （build_hook_name，#182 评审）：两条路径都产出
    f"plugin:{plugin_id}:{handler_name}"，与旧 PluginManager 逐字一致。"""
    plugin_dir = tmp_path / "legacy_hook"
    plugin_dir.mkdir()
    (plugin_dir / "backend").mkdir()
    (plugin_dir / "backend" / "plugin.py").write_text(
        "from agent.lifecycle.types import PreToolCtx\n"
        "from agent.plugins import Plugin, on_tool_pre\n"
        "class LegacyHook(Plugin):\n"
        "    name = 'legacy_hook'\n"
        "    @on_tool_pre(tool_name='shell')\n"
        "    async def guard(self, event: PreToolCtx):\n"
        "        return None\n",
        encoding="utf-8",
    )
    bus = EventBus()
    kernel = make_kernel([tmp_path], event_bus=bus)
    await kernel.load_all()

    assert [h.name for h in kernel.tool_hooks] == ["plugin:legacy_hook:guard"]


@pytest.mark.asyncio
async def test_direct_event_bus_subscription_unbound_on_unload(tmp_path: Path):
    """修复既有缺陷：插件在 initialize 里直接 event_bus.on 且不自行 off。"""
    plugin_dir = tmp_path / "direct_sub" / "backend"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.py").write_text(
        """
from agent.lifecycle.types import BeforeTurnCtx
from agent.plugins import Plugin

calls: list[str] = []


class DirectSub(Plugin):
    name = "direct_sub"

    async def initialize(self):
        # 直接订阅且从不 off —— 旧 PluginManager 卸载后会残留
        self.context.event_bus.on(BeforeTurnCtx, self._on_turn)

    async def _on_turn(self, event):
        calls.append(event.session_key)
        return event
""".strip(),
        encoding="utf-8",
    )
    bus = EventBus()
    kernel = make_kernel([tmp_path], event_bus=bus)
    await kernel.load_all()

    import sys

    module = next(
        m for k, m in sys.modules.items()
        if k.startswith("akasic_plugin_") and k.endswith("_direct_sub")
    )
    _ = await bus.emit(before_turn_ctx(session_key="test:live"))
    assert module.calls == ["test:live"]

    _ = await kernel.unload("direct_sub")
    _ = await bus.emit(before_turn_ctx(session_key="test:stale"))
    assert module.calls == ["test:live"]


@pytest.mark.asyncio
async def test_legacy_tool_registered_then_unregistered(tmp_path: Path):
    stage_plugin_fixture("weather", tmp_path)
    bus = EventBus()
    tools = ToolRegistry()
    kernel = make_kernel([tmp_path], event_bus=bus, tools=tools)
    await kernel.load_all()

    result = await tools.execute("get_weather", {"city": "巴黎"})
    assert "巴黎" in str(result)

    _ = await kernel.unload("weather")
    assert tools.get_tool("get_weather") is None


@pytest.mark.asyncio
async def test_init_failure_rolls_back_only_failed_plugin(tmp_path: Path):
    stage_plugin_fixture("hello", tmp_path)
    broken_dir = tmp_path / "zbroken" / "backend"
    broken_dir.mkdir(parents=True)
    (broken_dir / "plugin.py").write_text(
        """
from agent.lifecycle.types import BeforeTurnCtx
from agent.plugins import Plugin, tool


class Broken(Plugin):
    name = "zbroken"

    @tool("broken_tool")
    async def broken_tool(self, event, city: str = ""):
        return "never"

    async def initialize(self):
        self.context.event_bus.on(BeforeTurnCtx, self._on_turn)
        raise RuntimeError("init boom")

    async def _on_turn(self, event):
        event.extra_metadata["broken_touched"] = True
        return event
""".strip(),
        encoding="utf-8",
    )
    bus = EventBus()
    tools = ToolRegistry()
    kernel = make_kernel([tmp_path], event_bus=bus, tools=tools)
    await kernel.load_all()

    # 失败插件的工具与订阅全部回滚，健康插件不受影响
    assert kernel.loaded_count == 1
    assert tools.get_tool("broken_tool") is None
    result = await bus.emit(before_turn_ctx())
    assert result.extra_metadata.get("hello_touched") is True
    assert "broken_touched" not in result.extra_metadata


@pytest.mark.asyncio
async def test_strict_mode_raises_on_init_failure(tmp_path: Path):
    broken_dir = tmp_path / "broken" / "backend"
    broken_dir.mkdir(parents=True)
    (broken_dir / "plugin.py").write_text(
        "from agent.plugins import Plugin\n"
        "class Broken(Plugin):\n"
        "    name = 'broken'\n"
        "    async def initialize(self):\n"
        "        raise RuntimeError('candidate failure')\n",
        encoding="utf-8",
    )
    kernel = make_kernel([tmp_path], event_bus=EventBus(), namespace="candidate", strict=True)
    with pytest.raises(Exception, match="candidate failure"):
        await kernel.load_all()
    assert kernel.loaded_count == 0


@pytest.mark.asyncio
async def test_legacy_plugin_config_migrates_from_the_pre_move_plugin_root(
    tmp_path: Path,
):
    """插件包上移前遗留的 `plugin_config.json` 必须在装配 legacy 插件前迁移。

    `_load_plugin_config`（被 legacy 适配器复用）只从新插件目录读
    `plugin_config.json`；不迁移的话用户此前的配置覆盖会静默失效（#178 复审 #4）。
    """
    plugins_root = tmp_path / "plugins"
    plugin_dir = plugins_root / "configured"
    backend_dir = plugin_dir / "backend"
    backend_dir.mkdir(parents=True)
    _ = (plugin_dir / "_conf_schema.json").write_text(
        json.dumps({"max_results": {"default": 5}}), encoding="utf-8"
    )
    _ = (backend_dir / "plugin.py").write_text(
        """
from agent.lifecycle.types import BeforeTurnCtx
from agent.plugins import Plugin


class Configured(Plugin):
    name = "configured"

    async def initialize(self):
        self.context.event_bus.on(BeforeTurnCtx, self._on_turn)

    async def _on_turn(self, event):
        event.extra_metadata["max_results"] = self.context.config.get("max_results")
        return event
""".strip(),
        encoding="utf-8",
    )
    legacy_root = tmp_path / "apps" / "backend" / "plugins"
    legacy_config = legacy_root / "configured" / "plugin_config.json"
    legacy_config.parent.mkdir(parents=True)
    _ = legacy_config.write_text(json.dumps({"max_results": 42}), encoding="utf-8")

    bus = EventBus()
    kernel = PluginKernel(
        [plugins_root],
        services=HostServices(
            event_bus=bus,
            workspace=tmp_path / "workspace",
            legacy_plugin_root=legacy_root,
        ),
    )
    await kernel.load_all()

    result = await bus.emit(before_turn_ctx())
    assert result.extra_metadata.get("max_results") == 42
    assert (plugin_dir / "plugin_config.json").exists()
    assert not legacy_config.exists()


@pytest.mark.asyncio
async def test_terminate_runs_before_unbind(tmp_path: Path):
    """terminate 中插件自行 off 自己的订阅（scene_awareness 模式）不应报错。"""
    plugin_dir = tmp_path / "self_off" / "backend"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.py").write_text(
        """
from agent.lifecycle.types import BeforeTurnCtx
from agent.plugins import Plugin

terminated: list[bool] = []


class SelfOff(Plugin):
    name = "self_off"

    async def initialize(self):
        self._handler = self._on_turn
        self.context.event_bus.on(BeforeTurnCtx, self._handler)

    async def terminate(self):
        self.context.event_bus.off(BeforeTurnCtx, self._handler)
        terminated.append(True)

    async def _on_turn(self, event):
        return event
""".strip(),
        encoding="utf-8",
    )
    bus = EventBus()
    kernel = make_kernel([tmp_path], event_bus=bus)
    await kernel.load_all()

    import sys

    module = next(
        m for k, m in sys.modules.items()
        if k.startswith("akasic_plugin_") and k.endswith("_self_off")
    )
    await kernel.terminate_all()
    assert module.terminated == [True]
