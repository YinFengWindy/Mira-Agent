"""legacy 适配器行为：旧 Plugin ABC 插件零改动跑在内核上，卸载全量回收。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bus.event_bus import EventBus
from agent.tools.registry import ToolRegistry

from tests.backend.agent.plugin_host.conftest import (
    FIXTURES_DIR,
    before_turn_ctx,
    make_kernel,
)


@pytest.mark.asyncio
async def test_legacy_decorator_handler_fires_and_unbinds_on_unload(tmp_path: Path):
    shutil.copytree(FIXTURES_DIR / "hello", tmp_path / "hello")
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
async def test_direct_event_bus_subscription_unbound_on_unload(tmp_path: Path):
    """修复既有缺陷：插件在 initialize 里直接 event_bus.on 且不自行 off。"""
    plugin_dir = tmp_path / "direct_sub"
    plugin_dir.mkdir()
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
    shutil.copytree(FIXTURES_DIR / "weather", tmp_path / "weather")
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
    shutil.copytree(FIXTURES_DIR / "hello", tmp_path / "hello")
    broken_dir = tmp_path / "zbroken"
    broken_dir.mkdir()
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
    broken_dir = tmp_path / "broken"
    broken_dir.mkdir()
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
async def test_terminate_runs_before_unbind(tmp_path: Path):
    """terminate 中插件自行 off 自己的订阅（scene_awareness 模式）不应报错。"""
    plugin_dir = tmp_path / "self_off"
    plugin_dir.mkdir()
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
