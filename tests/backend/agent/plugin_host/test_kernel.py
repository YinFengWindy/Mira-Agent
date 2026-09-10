"""内核行为：发现、v2 装配、capability 门控、启停与聚合面。"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.plugin_host import PluginState
from agent.plugin_host.plugin_data import plugin_data_dir
from agent.tools.registry import ToolRegistry
from bus.event_bus import EventBus

from tests.backend.agent.plugin_host.conftest import (
    REPOSITORY_ROOT,
    before_turn_ctx,
    make_kernel,
    stage_plugin_fixture,
)

_EXPECTED_TOP_LEVEL_PLUGINS = {
    "akasha",
    "citation",
    "context_pressure",
    "default_memory",
    "desktop_pet",
    "meme",
    "novelai",
    "observe",
    "plugin_undo",
    "qqbot",
    "relationship_proactive",
    "scene_awareness",
    "setup_helper",
    "shell_restore",
    "shell_safety",
    "status_commands",
    "tool_loop_guard",
}


def test_discover_finds_all_top_level_plugins():
    """插件目录迁至仓库顶层 `plugins/` 后，内核发现路径必须能找到全部 17 个插件（#178）。"""
    plugins_dir = REPOSITORY_ROOT / "plugins"
    kernel = make_kernel([plugins_dir], event_bus=EventBus())

    names = {record.name for record in kernel.discover()}

    assert names == _EXPECTED_TOP_LEVEL_PLUGINS


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
    (plugin_dir / "backend").mkdir(parents=True)
    (plugin_dir / "backend" / "plugin.py").write_text(_V2_PLUGIN, encoding="utf-8")
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
    # kv 落在 workspace 而不是插件目录（issue #209）；夹具把插件目录的父目录当
    # workspace，所以这里是 tmp_path/plugins/v2demo/kv.json
    assert (plugin_data_dir(tmp_path, "v2demo") / "kv.json").exists()
    assert not (plugin_dir / ".kv.json").exists()

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
    (plugin_dir / "backend").mkdir(parents=True)
    (plugin_dir / "backend" / "plugin.py").write_text(
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
    (plugin_dir / "backend").mkdir(parents=True)
    (plugin_dir / "backend" / "plugin.py").write_text(
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
    stage_plugin_fixture("hello", tmp_path)
    (tmp_path / "hello" / "plugin.disabled").write_text("", encoding="utf-8")
    kernel = make_kernel([tmp_path], event_bus=EventBus())
    await kernel.load_all()

    assert kernel.loaded_count == 0
    assert any(item["state"] == PluginState.DISABLED.name for item in kernel.states())


@pytest.mark.asyncio
async def test_duplicate_plugin_name_first_wins(tmp_path: Path):
    _ = stage_plugin_fixture("hello", tmp_path)
    _ = stage_plugin_fixture("weather", tmp_path)
    kernel = make_kernel([tmp_path, tmp_path], event_bus=EventBus())

    records = kernel.discover()

    # 同一目录被列两次，同名插件只应出现一次
    assert {r.name for r in records} == {"hello", "weather"}
    assert len(records) == 2


@pytest.mark.asyncio
async def test_runtime_disable_then_enable(tmp_path: Path):
    stage_plugin_fixture("hello", tmp_path)
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
    stage_plugin_fixture("hello", tmp_path)
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
    plugin_dir = tmp_path / "cmds" / "backend"
    plugin_dir.mkdir(parents=True)
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


_RPC_PLUGIN = """
async def _ping(payload):
    return {"pong": payload.get("value")}


async def setup(ctx):
    ctx.rpc.register("ping", _ping)
""".strip()

_RPC_MANIFEST = "api: 2\nid: rpcdemo\ncapabilities:\n  - rpc\n"


@pytest.mark.asyncio
async def test_v2_plugin_rpc_method_callable_then_gone_after_unload(tmp_path: Path):
    plugin_dir = tmp_path / "rpcdemo"
    (plugin_dir / "backend").mkdir(parents=True)
    (plugin_dir / "backend" / "plugin.py").write_text(_RPC_PLUGIN, encoding="utf-8")
    (plugin_dir / "manifest.yaml").write_text(_RPC_MANIFEST, encoding="utf-8")
    kernel = make_kernel([tmp_path], event_bus=EventBus())
    await kernel.load_all()

    resolved = kernel.rpc.resolve("plugin.rpcdemo.ping")
    assert resolved is not None
    _, handler = resolved
    assert await handler({"value": 1}) == {"pong": 1}

    _ = await kernel.unload("rpcdemo")

    # 插件卸载后其 RPC 方法立即不可调用
    assert kernel.rpc.resolve("plugin.rpcdemo.ping") is None


@pytest.mark.asyncio
async def test_weather_tool_via_facade(tmp_path: Path):
    stage_plugin_fixture("weather", tmp_path)
    tools = ToolRegistry()
    kernel = make_kernel([tmp_path], event_bus=EventBus(), tools=tools)
    await kernel.load_all()
    assert tools.get_tool("get_weather") is not None
    await kernel.terminate_all()
    assert tools.get_tool("get_weather") is None
