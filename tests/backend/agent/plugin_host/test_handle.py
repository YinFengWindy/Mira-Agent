"""handle.py 行为：插件句柄记账与生命周期状态迁移（含失败与禁用路径）。"""

from __future__ import annotations

from pathlib import Path

from agent.plugin_host.handle import (
    PluginHandle,
    PluginRecord,
    PluginState,
)
from agent.plugin_host.manifest import PluginManifest


def _make_handle(plugin_id: str = "demo") -> PluginHandle:
    record = PluginRecord(
        name=plugin_id,
        plugin_dir=Path("plugins") / plugin_id,
        entry_file=Path("plugins") / plugin_id / "plugin.py",
        import_path=f"akasic_plugin_plugins_{plugin_id}",
        manifest=PluginManifest(id=plugin_id),
    )
    return PluginHandle(record=record)


def test_new_handle_starts_discovered_with_empty_contributions():
    handle = _make_handle()
    assert handle.state is PluginState.DISCOVERED
    assert handle.instance is None
    assert handle.error is None
    assert handle.contributions.tool_hooks == []
    assert handle.contributions.phase_modules["before_turn"] == []


def test_plugin_id_comes_from_manifest_not_directory_name():
    record = PluginRecord(
        name="dir_name",
        plugin_dir=Path("plugins/dir_name"),
        entry_file=Path("plugins/dir_name/plugin.py"),
        import_path="akasic_plugin_plugins_dir_name",
        manifest=PluginManifest(id="manifest_id"),
    )
    assert PluginHandle(record=record).plugin_id == "manifest_id"


def test_describe_reports_state_and_error():
    handle = _make_handle()
    handle.state = PluginState.FAILED
    handle.error = RuntimeError("init boom")

    described = handle.describe()
    assert described["id"] == "demo"
    assert described["state"] == "FAILED"
    assert described["error"] == "init boom"


def test_describe_leaves_error_blank_when_healthy():
    handle = _make_handle()
    handle.state = PluginState.ACTIVE
    assert handle.describe()["error"] == ""


def test_handles_do_not_share_contribution_state():
    """default_factory 必须为每个句柄新建贡献容器，否则插件间会互相污染。"""
    first, second = _make_handle("a"), _make_handle("b")
    first.contributions.tool_names.append("tool_from_a")
    assert second.contributions.tool_names == []
    assert first.effects is not second.effects
