"""Shared core feature migration preserves independent switches and document contents."""

import tomllib

from agent.legacy_feature_preferences import migrate_boolean_preferences


def test_two_feature_migrations_preserve_explicit_keys_and_do_not_rewrite_again(
    tmp_path,
):
    path = tmp_path / "config.toml"
    path.write_text(
        "# retained\n[agent.proactive_strategies]\nscene_followup = true # explicit override\n[plugins.relationship_proactive]\nenabled = false\n[plugins.scene_awareness]\nenabled = false\n",
        encoding="utf-8",
    )
    migrations = [
        dict(
            section="proactive_strategies",
            keys=("scene_followup", "relationship"),
            legacy_id="relationship_proactive",
        ),
        dict(
            section="scene_observation", keys=("enabled",), legacy_id="scene_awareness"
        ),
    ]
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    for arguments in migrations:
        data = migrate_boolean_preferences(
            path, data, roots=(tmp_path / "plugins",), **arguments
        )
    assert data["agent"]["proactive_strategies"] == {
        "scene_followup": True,
        "relationship": False,
    }
    assert data["agent"]["scene_observation"] == {"enabled": False}
    migrated = path.read_bytes()
    for arguments in migrations:
        data = migrate_boolean_preferences(
            path, data, roots=(tmp_path / "plugins",), **arguments
        )
    assert path.read_bytes() == migrated
    assert b"# retained" in migrated
