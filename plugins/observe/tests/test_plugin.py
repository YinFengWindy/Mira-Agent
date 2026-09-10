from __future__ import annotations

import asyncio
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from agent.plugin_host import HostServices, PluginKernel
from bus.event_bus import EventBus
from bus.events_lifecycle import TurnCommitted

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_observe_kernel(
    tmp_path: Path, *, workspace: Path | None
) -> tuple[PluginKernel, EventBus]:
    root = tmp_path / "plugins"
    root.mkdir()
    shutil.copytree(_REPO_ROOT / "plugins" / "observe", root / "observe")
    bus = EventBus()
    kernel = PluginKernel([root], services=HostServices(event_bus=bus, workspace=workspace))
    return kernel, bus


def _turn_committed(**overrides: object) -> TurnCommitted:
    defaults: dict[str, object] = dict(
        session_key="cli:1",
        channel="cli",
        chat_id="1",
        input_message="hi",
        persisted_user_message="hi",
        assistant_response="hello",
        tools_used=[],
    )
    defaults.update(overrides)
    return TurnCommitted(**defaults)


async def _wait_for_turn_row(db_path: Path, *, timeout: float = 5.0) -> int:
    """Polls observe.db until the async writer task has committed a row."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if db_path.exists():
            with closing(sqlite3.connect(str(db_path))) as conn:
                count = conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
                if count:
                    return int(count)
        await asyncio.sleep(0.02)
    return 0


@pytest.mark.asyncio
async def test_setup_skips_without_workspace(tmp_path: Path) -> None:
    """workspace 缺失时插件仍加载成功但不贡献任何行为，对齐旧 initialize() 的早退。"""
    kernel, _bus = _load_observe_kernel(tmp_path, workspace=None)

    await kernel.load_all()

    assert kernel.loaded_count == 1
    _ = await kernel.terminate_all()


@pytest.mark.asyncio
async def test_turn_committed_event_reaches_writer_and_is_persisted(tmp_path: Path) -> None:
    """setup() 必须与旧 ObservePlugin.initialize() 等价：TurnCommitted 经事件订阅
    真正写入 observe.db（而不仅仅是"没抛异常"）。"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    kernel, bus = _load_observe_kernel(tmp_path, workspace=workspace)
    await kernel.load_all()
    assert kernel.loaded_count == 1

    _ = await bus.emit(_turn_committed())

    db_path = workspace / "observe" / "observe.db"
    row_count = await _wait_for_turn_row(db_path)
    assert row_count == 1


@pytest.mark.asyncio
async def test_unload_cancels_background_tasks_and_uninstalls_collector_cleanly(
    tmp_path: Path,
) -> None:
    """卸载必须干净收尾：不抛异常，且卸载后事件不再落库（effect 真正生效）。"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    kernel, bus = _load_observe_kernel(tmp_path, workspace=workspace)
    await kernel.load_all()
    _ = await bus.emit(_turn_committed(session_key="cli:1"))
    db_path = workspace / "observe" / "observe.db"
    _ = await _wait_for_turn_row(db_path)

    errors = await kernel.unload("observe")
    assert errors == []

    # 卸载后订阅应已随 effect 撤销；再 emit 不应再增加行数
    row_count_before = await _wait_for_turn_row(db_path, timeout=0.2)
    _ = await bus.emit(_turn_committed(session_key="cli:2"))
    await asyncio.sleep(0.1)
    with closing(sqlite3.connect(str(db_path))) as conn:
        row_count_after = conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
    assert row_count_after == row_count_before
