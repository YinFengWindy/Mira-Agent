from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.lifecycle.types import AfterTurnCtx, BeforeTurnCtx
from agent.plugin_host import HostServices, PluginKernel, PluginState
from bus.event_bus import EventBus
from bus.events_lifecycle import ProactiveMessageCommitted

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_scene_awareness_kernel(
    tmp_path: Path, *, workspace: Path | None, session_manager: object = None
) -> tuple[PluginKernel, EventBus]:
    root = tmp_path / "plugins"
    root.mkdir()
    shutil.copytree(
        _REPO_ROOT / "plugins" / "scene_awareness", root / "scene_awareness"
    )
    bus = EventBus()
    kernel = PluginKernel(
        [root],
        services=HostServices(
            event_bus=bus, workspace=workspace, session_manager=session_manager
        ),
    )
    return kernel, bus


def _before_turn_ctx(**overrides: object) -> BeforeTurnCtx:
    defaults: dict[str, object] = dict(
        session_key="cli:1",
        channel="cli",
        chat_id="1",
        content="hello",
        timestamp=datetime.now(timezone.utc),
        retrieved_memory_block="",
        retrieval_trace_raw=None,
        history_messages=(),
    )
    defaults.update(overrides)
    return BeforeTurnCtx(**defaults)


def _after_turn_ctx(**overrides: object) -> AfterTurnCtx:
    defaults: dict[str, object] = dict(
        session_key="cli:1",
        channel="cli",
        chat_id="1",
        reply="hi there",
        tools_used=(),
        thinking=None,
        will_dispatch=True,
    )
    defaults.update(overrides)
    return AfterTurnCtx(**defaults)


@pytest.mark.asyncio
async def test_setup_fails_without_workspace(tmp_path: Path) -> None:
    """workspace 缺失时插件加载失败并回滚，对齐旧 initialize() 的 raise。"""
    kernel, _bus = _load_scene_awareness_kernel(tmp_path, workspace=None)

    await kernel.load_all()

    assert kernel.loaded_count == 0
    states = {item["id"]: item for item in kernel.states()}
    assert states["scene_awareness"]["state"] == PluginState.FAILED.name
    assert "workspace" in states["scene_awareness"]["error"]


@pytest.mark.asyncio
async def test_setup_wires_before_after_turn_and_proactive_events(
    tmp_path: Path,
) -> None:
    """setup() 必须贡献与旧 SceneAwarenessPlugin 等价的三个事件订阅，且卸载后
    干净收尾（controller.terminate() 不抛异常，effect 真正撤销订阅）。"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    session_manager = SimpleNamespace(get_or_create=lambda key: SimpleNamespace(
        metadata={}, messages=()
    ))
    kernel, bus = _load_scene_awareness_kernel(
        tmp_path, workspace=workspace, session_manager=session_manager
    )

    await kernel.load_all()
    assert kernel.loaded_count == 1

    # before_turn 是 GATE：handler 必须把（未被改写的）ctx 原样传回
    before_ctx = _before_turn_ctx()
    result = await bus.emit(before_ctx)
    assert result is before_ctx

    # after_turn / proactive 只需确认订阅生效且不抛异常（controller 内部因缺少
    # light_provider 静默跳过调度，这部分业务逻辑由 test_controller.py 覆盖）
    _ = await bus.emit(_after_turn_ctx())
    await bus.fanout(
        ProactiveMessageCommitted(
            session_key="cli:1",
            channel="cli",
            chat_id="1",
            role_id="",
            assistant_response="hi",
            tools_used=(),
        )
    )

    errors = await kernel.unload("scene_awareness")
    assert errors == []

    # 卸载后事件订阅应已撤销：再次 emit 必须不再命中任何 handler，
    # bus.emit 在没有 handler 时原样返回同一个对象。
    after_before_ctx = _before_turn_ctx(session_key="cli:2")
    result_after_unload = await bus.emit(after_before_ctx)
    assert result_after_unload is after_before_ctx
