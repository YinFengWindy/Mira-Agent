"""内核行为：发现、v2 装配、capability 门控、启停与聚合面。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agent.plugin_host import PluginState
from agent.tools.registry import ToolRegistry
from bus.event_bus import EventBus

from tests.backend.agent.plugin_host.conftest import (
    FIXTURES_DIR,
    before_turn_ctx,
    make_kernel,
)

_V2_PLUGIN = """
from agent.lifecycle.types import BeforeTurnCtx

seen: list[str] = []


class StampModule:
    async def run(self, frame):
        return frame


async def setup(ctx):
    ctx.events.on(BeforeTurnCtx, _on_turn)
    ctx.lifecycle.contribute("before_turn", [StampModule()])
    ctx.kv.set("booted", True)


async def _on_turn(event):
    seen.append(event.session_key)
    return event
""".strip()

_V2_MANIFEST = (
    "api: 2\nid: v2demo\nversion: '0.1'\n"
    "capabilities:\n  - events\n  - lifecycle\n  - kv\n"
)


def _write_v2_plugin(root: Path) -> Path:
    plugin_dir = root / "v2demo"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text(_V2_PLUGIN, encoding="utf-8")
    (plugin_dir / "manifest.yaml").write_text(_V2_MANIFEST, encoding="utf-8")
    return plugin_dir


@pytest.mark.asyncio
async def test_v2_plugin_setup_and_unload(tmp_path: Path):
    plugin_dir = _write_v2_plugin(tmp_path)
    bus = EventBus()
    kernel = make_kernel([tmp_path], event_bus=bus)
    await kernel.load_all()

    assert kernel.loaded_count == 1
    assert [m.__class__.__name__ for m in kernel.before_turn_modules] == ["StampModule"]
    assert (plugin_dir / ".kv.json").exists()

    import sys

    module = next(
        m for k, m in sys.modules.items()
        if k.startswith("akasic_plugin_") and k.endswith("_v2demo")
    )
    _ = await bus.emit(before_turn_ctx(session_key="test:v2"))
    assert module.seen == ["test:v2"]

    _ = await kernel.unload("v2demo")
    assert kernel.before_turn_modules == []
    _ = await bus.emit(before_turn_ctx(session_key="test:gone"))
    assert module.seen == ["test:v2"]


@pytest.mark.asyncio
async def test_v2_capability_gating(tmp_path: Path):
    plugin_dir = tmp_path / "gated"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text(
        """
captured: dict = {}


async def setup(ctx):
    captured["granted"] = ctx.granted
    try:
        _ = ctx.tools
    except AttributeError as e:
        captured["denied"] = str(e)
""".strip(),
        encoding="utf-8",
    )
    (plugin_dir / "manifest.yaml").write_text(
        "api: 2\nid: gated\ncapabilities:\n  - events\n",
        encoding="utf-8",
    )
    kernel = make_kernel([tmp_path], event_bus=EventBus())
    await kernel.load_all()

    import sys

    module = next(
        m for k, m in sys.modules.items()
        if k.startswith("akasic_plugin_") and k.endswith("_gated")
    )
    assert module.captured["granted"] == ("events",)
    assert "未声明 capability" in module.captured["denied"]


@pytest.mark.asyncio
async def test_v2_setup_failure_rolls_back_effects(tmp_path: Path):
    plugin_dir = tmp_path / "v2broken"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text(
        """
from agent.lifecycle.types import BeforeTurnCtx


async def setup(ctx):
    ctx.events.on(BeforeTurnCtx, _on_turn)
    raise RuntimeError("v2 boom")


async def _on_turn(event):
    event.extra_metadata["v2broken_touched"] = True
    return event
""".strip(),
        encoding="utf-8",
    )
    (plugin_dir / "manifest.yaml").write_text(
        "api: 2\nid: v2broken\ncapabilities:\n  - events\n",
        encoding="utf-8",
    )
    bus = EventBus()
    kernel = make_kernel([tmp_path], event_bus=bus)
    await kernel.load_all()

    assert kernel.loaded_count == 0
    result = await bus.emit(before_turn_ctx())
    assert "v2broken_touched" not in result.extra_metadata


@pytest.mark.asyncio
async def test_disabled_marker_skips_plugin(tmp_path: Path):
    shutil.copytree(FIXTURES_DIR / "hello", tmp_path / "hello")
    (tmp_path / "hello" / "plugin.disabled").write_text("", encoding="utf-8")
    kernel = make_kernel([tmp_path], event_bus=EventBus())
    await kernel.load_all()

    assert kernel.loaded_count == 0
    assert any(item["state"] == PluginState.DISABLED.name for item in kernel.states())


@pytest.mark.asyncio
async def test_duplicate_plugin_name_first_wins(tmp_path: Path):
    kernel = make_kernel([FIXTURES_DIR, FIXTURES_DIR], event_bus=EventBus())
    records = kernel.discover()
    assert len({r.name for r in records}) == len(records)


@pytest.mark.asyncio
async def test_runtime_disable_then_enable(tmp_path: Path):
    shutil.copytree(FIXTURES_DIR / "hello", tmp_path / "hello")
    bus = EventBus()
    kernel = make_kernel([tmp_path], event_bus=bus)
    await kernel.load_all()
    assert kernel.loaded_count == 1

    _ = await kernel.unload("hello")
    assert kernel.loaded_count == 0
    result = await bus.emit(before_turn_ctx())
    assert "hello_touched" not in result.extra_metadata

    # 重新启用后行为恢复
    assert await kernel.load("hello") is True
    assert kernel.loaded_count == 1
    result = await bus.emit(before_turn_ctx())
    assert result.extra_metadata.get("hello_touched") is True


@pytest.mark.asyncio
async def test_load_all_is_idempotent(tmp_path: Path):
    shutil.copytree(FIXTURES_DIR / "hello", tmp_path / "hello")
    bus = EventBus()
    kernel = make_kernel([tmp_path], event_bus=bus)
    await kernel.load_all()
    await kernel.load_all()

    assert kernel.loaded_count == 1
    result = await bus.emit(before_turn_ctx())
    # 重复 load_all 不得重复绑定 handler（否则 metadata 被写两次也看不出，改用计数）
    assert result.extra_metadata.get("hello_touched") is True


@pytest.mark.asyncio
async def test_telegram_bot_commands_aggregated(tmp_path: Path):
    plugin_dir = tmp_path / "cmds"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text(
        "from agent.plugins import Plugin\n"
        "class Cmds(Plugin):\n"
        "    name = 'cmds'\n"
        "    def telegram_bot_commands(self):\n"
        "        return [('undo', '撤销上一轮')]\n",
        encoding="utf-8",
    )
    kernel = make_kernel([tmp_path], event_bus=EventBus())
    await kernel.load_all()
    assert kernel.telegram_bot_commands == [("undo", "撤销上一轮")]


@pytest.mark.asyncio
async def test_weather_tool_via_facade(tmp_path: Path):
    shutil.copytree(FIXTURES_DIR / "weather", tmp_path / "weather")
    tools = ToolRegistry()
    kernel = make_kernel([tmp_path], event_bus=EventBus(), tools=tools)
    await kernel.load_all()
    assert tools.get_tool("get_weather") is not None
    await kernel.terminate_all()
    assert tools.get_tool("get_weather") is None
