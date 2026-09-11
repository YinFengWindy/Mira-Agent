import tomllib

import pytest

from agent import scene_preferences as prefs
from agent.config import load_config_text


@pytest.mark.parametrize("marker", ["package", "legacy", "config"])
def test_disabled_preference_migrates_idempotently_without_other_file_writes(
    tmp_path, monkeypatch, marker
):
    monkeypatch.setattr(prefs, "resource_root", lambda: tmp_path / "package")
    monkeypatch.setattr(prefs, "REPOSITORY_ROOT", tmp_path / "legacy")
    if marker != "config":
        root = (
            tmp_path / "package" / "plugins"
            if marker == "package"
            else tmp_path / "legacy" / "apps" / "backend" / "plugins"
        )
        path = root / "scene_awareness" / "plugin.disabled"
        path.parent.mkdir(parents=True)
        path.touch()
    path = tmp_path / "config.toml"
    text = "# keep comment\n[agent]\nmax_tokens = 1234\n" + (
        "[plugins.scene_awareness]\nenabled = false\n" if marker == "config" else ""
    )
    path.write_text(text, encoding="utf-8")
    data = prefs.migrate_scene_preferences(path, tomllib.loads(text))
    assert data["agent"]["scene_observation"]["enabled"] is False
    migrated = path.read_text(encoding="utf-8")
    assert "# keep comment" in migrated
    assert prefs.migrate_scene_preferences(path, data) == data
    assert path.read_text(encoding="utf-8") == migrated
    assert not (tmp_path / "roles").exists()
    assert not (tmp_path / ".config-transactions").exists()
    path.write_text(
        migrated.replace("enabled = false", "enabled = true"), encoding="utf-8"
    )
    assert (
        prefs.migrate_scene_preferences(
            path, tomllib.loads(path.read_text(encoding="utf-8"))
        )["agent"]["scene_observation"]["enabled"]
        is True
    )


def test_candidate_config_uses_explicit_core_preference_and_rejects_invalid_type():
    assert (
        load_config_text(
            "[plugins.scene_awareness]\nenabled = false\n"
        ).scene_observation_enabled
        is False
    )
    assert (
        load_config_text(
            "[agent.scene_observation]\nenabled = true\n[plugins.scene_awareness]\nenabled = false\n"
        ).scene_observation_enabled
        is True
    )
    with pytest.raises(ValueError, match="boolean"):
        load_config_text('[agent.scene_observation]\nenabled = "false"\n')
