"""插件私有数据落在 workspace，而不是插件目录（issue #209）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.plugin_host.plugin_data import open_plugin_kv, plugin_data_dir


def test_kv_lands_under_the_workspace_not_the_plugin_directory(tmp_path: Path):
    """插件目录在打包形态下属于只读的应用安装目录，写进去的数据升级即丢。"""
    workspace = tmp_path / "workspace"
    plugin_dir = tmp_path / "plugins" / "demo"
    plugin_dir.mkdir(parents=True)

    store = open_plugin_kv(workspace=workspace, plugin_id="demo", plugin_dir=plugin_dir)
    store.set("counter", 3)

    assert (plugin_data_dir(workspace, "demo") / "kv.json").is_file()
    assert not (plugin_dir / ".kv.json").exists()


def test_missing_workspace_fails_loudly_instead_of_falling_back(tmp_path: Path):
    """宿主没给 workspace 时必须报错，不能悄悄退回写插件目录——那正是 #209 的病根。"""
    plugin_dir = tmp_path / "demo"
    plugin_dir.mkdir()

    with pytest.raises(RuntimeError, match="workspace"):
        _ = open_plugin_kv(workspace=None, plugin_id="demo", plugin_dir=plugin_dir)

    assert not (plugin_dir / ".kv.json").exists()


def test_legacy_kv_in_the_plugin_directory_is_migrated_once(tmp_path: Path):
    """已有用户的数据存在插件目录里；不迁移会让 novelai 的冷却与场景去重归零。"""
    workspace = tmp_path / "workspace"
    plugin_dir = tmp_path / "plugins" / "novelai"
    plugin_dir.mkdir(parents=True)
    legacy = plugin_dir / ".kv.json"
    _ = legacy.write_text(
        json.dumps({"auto_cg_sessions": {"role:mira": {"turn": 7}}}), encoding="utf-8"
    )

    store = open_plugin_kv(
        workspace=workspace, plugin_id="novelai", plugin_dir=plugin_dir
    )

    assert store.get("auto_cg_sessions") == {"role:mira": {"turn": 7}}
    assert not legacy.exists(), "迁移后旧文件应被移除，避免两份数据并存"


def test_migration_never_overwrites_existing_workspace_data(tmp_path: Path):
    """workspace 已有数据时，插件目录里的陈旧残留不得覆盖它。"""
    workspace = tmp_path / "workspace"
    plugin_dir = tmp_path / "plugins" / "demo"
    plugin_dir.mkdir(parents=True)
    target = plugin_data_dir(workspace, "demo") / "kv.json"
    target.parent.mkdir(parents=True)
    _ = target.write_text(json.dumps({"value": "current"}), encoding="utf-8")
    _ = (plugin_dir / ".kv.json").write_text(
        json.dumps({"value": "stale"}), encoding="utf-8"
    )

    store = open_plugin_kv(workspace=workspace, plugin_id="demo", plugin_dir=plugin_dir)

    assert store.get("value") == "current"
