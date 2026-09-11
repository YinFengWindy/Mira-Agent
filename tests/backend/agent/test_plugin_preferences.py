"""Persisted upgrade behavior for agent.plugin_preferences."""

from copy import deepcopy
import tomllib

import pytest

import agent.plugin_preferences as preferences


def _environment(tmp_path, monkeypatch, text=""):
    source = tmp_path / "checkout"
    packages = source / "plugins"
    packages.mkdir(parents=True)
    monkeypatch.setattr(preferences, "plugin_roots", lambda: [packages])
    monkeypatch.setattr(preferences, "REPOSITORY_ROOT", source)
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    _package(packages, "demo", "demo")
    return path, packages, source / "apps/backend/plugins"


def _package(root, directory, plugin_id):
    package = root / directory
    (package / "backend").mkdir(parents=True, exist_ok=True)
    (package / "manifest.yaml").write_text(
        f"api: 2\nid: {plugin_id}\ncapabilities: []\n", encoding="utf-8"
    )
    (package / "backend/plugin.py").write_text(
        "async def setup(ctx):\n    pass\n", encoding="utf-8"
    )


def _marker(root, name):
    path = root / name / "plugin.disabled"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("disabled by user", encoding="utf-8")
    return path


@pytest.mark.parametrize("old_location", [False, True])
def test_upgrade_preserves_disabled_state_and_is_idempotent(
    tmp_path, monkeypatch, old_location
):
    path, packages, legacy = _environment(
        tmp_path,
        monkeypatch,
        '[plugins.demo]\nsecret = "keep"\n[plugins.demo.nested]\nports = [1, 2]\n',
    )
    marker = _marker(legacy if old_location else packages, "demo")
    original = tomllib.loads(path.read_text(encoding="utf-8"))
    updated = preferences.migrate_plugin_preferences(path, original)
    assert updated["plugins"]["demo"] == {
        "secret": "keep",
        "nested": {"ports": [1, 2]},
        "enabled": False,
    }
    assert "enabled" not in original["plugins"]["demo"]
    assert tomllib.loads(path.read_text(encoding="utf-8")) == updated
    before = path.read_bytes()
    assert preferences.migrate_plugin_preferences(path, updated) == updated
    assert path.read_bytes() == before
    assert marker.read_text(encoding="utf-8") == "disabled by user"


@pytest.mark.parametrize("enabled", [True, False])
def test_explicit_configuration_wins_over_residual_marker(
    tmp_path, monkeypatch, enabled
):
    path, packages, _ = _environment(
        tmp_path, monkeypatch, f"[plugins.demo]\nenabled = {str(enabled).lower()}\n"
    )
    _marker(packages, "demo")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    before = path.read_bytes()
    assert preferences.migrate_plugin_preferences(path, data) is data
    assert path.read_bytes() == before


def test_failed_persistence_keeps_source_and_retries_cleanly(tmp_path, monkeypatch):
    path, packages, _ = _environment(tmp_path, monkeypatch)
    marker = _marker(packages, "demo")
    original = {}

    def fail(*args):
        raise OSError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(preferences, "atomic_save_text", fail)
        with pytest.raises(OSError, match="disk full"):
            preferences.migrate_plugin_preferences(path, original)
    assert path.read_text(encoding="utf-8") == ""
    assert original == {}
    assert marker.is_file()
    assert (
        preferences.migrate_plugin_preferences(path, original)["plugins"]["demo"][
            "enabled"
        ]
        is False
    )


def test_inline_quoted_and_nested_tables_keep_their_types(tmp_path, monkeypatch):
    path, packages, _ = _environment(
        tmp_path,
        monkeypatch,
        'plugins."demo.id" = { tokens = [1, 2], credentials = { secret = "value" } }\n',
    )
    _package(packages, "demo.id", "demo.id")
    _marker(packages, "demo.id")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    expected = deepcopy(data)
    expected["plugins"]["demo.id"]["enabled"] = False
    assert preferences.migrate_plugin_preferences(path, data) == expected
    assert tomllib.loads(path.read_text(encoding="utf-8")) == expected


def test_retired_core_markers_are_left_to_their_owner(tmp_path, monkeypatch):
    path, packages, _ = _environment(tmp_path, monkeypatch)
    for name in ("relationship_proactive", "scene_awareness"):
        _marker(packages, name)
    assert preferences.migrate_plugin_preferences(path, {}) == {}
    assert path.read_bytes() == b""


@pytest.mark.asyncio
@pytest.mark.parametrize("old_location", [False, True])
async def test_marker_directory_resolves_to_current_manifest_identity(
    tmp_path, monkeypatch, old_location
):
    from agent.plugin_host import HostServices, PluginKernel
    from bus.event_bus import EventBus

    path, packages, legacy = _environment(tmp_path, monkeypatch)
    _package(packages, "folder", "stable-id")
    marker = _marker(legacy if old_location else packages, "folder")
    migrated = preferences.migrate_plugin_preferences(path, {})
    assert migrated == {"plugins": {"stable-id": {"enabled": False}}}
    kernel = PluginKernel(
        [packages],
        services=HostServices(event_bus=EventBus(), plugin_configs=migrated["plugins"]),
    )
    try:
        await kernel.load_all()
        assert (
            next(row for row in kernel.states() if row["id"] == "stable-id")["state"]
            == "DISABLED"
        )
        assert marker.is_file()
    finally:
        await kernel.terminate_all()


def test_orphan_marker_is_retained_until_current_package_identity_is_known(
    tmp_path, monkeypatch
):
    path, packages, legacy = _environment(tmp_path, monkeypatch)
    marker = _marker(legacy, "not-installed")
    assert preferences.migrate_plugin_preferences(path, {}) == {}
    assert path.read_bytes() == b""
    assert marker.is_file()
    _package(packages, "not-installed", "new-id")
    assert preferences.migrate_plugin_preferences(path, {}) == {
        "plugins": {"new-id": {"enabled": False}}
    }
