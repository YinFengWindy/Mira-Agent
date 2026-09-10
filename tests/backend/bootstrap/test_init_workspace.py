import json
import tomllib

from bootstrap import init_workspace as workspace_init


def test_init_workspace_creates_expected_assets(tmp_path):
    config_path = tmp_path / "config.toml"
    workspace = tmp_path / "workspace"

    summary = workspace_init.init_workspace(
        config_path=config_path,
        workspace=workspace,
    )

    assert config_path.exists()
    config_text = config_path.read_text(encoding="utf-8")
    registrations = tomllib.loads(config_text)["llm"]["registrations"]
    assert registrations == []
    assert "[llm.vl]" not in config_text
    assert (workspace / "sessions.db").exists()
    assert (workspace / "observe").is_dir()
    assert (workspace / "memory" / "consolidation_writes.db").exists()
    assert (workspace / "memory" / "journal").is_dir()
    assert (workspace / "memory" / "memory2.db").exists()
    assert json.loads(
        (workspace / "mcp_servers.json").read_text(encoding="utf-8")
    ) == {"servers": {}}
    assert json.loads(
        (workspace / "proactive_sources.json").read_text(encoding="utf-8")
    ) == {"sources": []}
    assert (workspace / "skills").is_dir()
    assert not (workspace / "drift" / "skills").exists()
    assert (workspace / "roles" / "roles.json").exists()
    assert json.loads(
        (workspace / "roles" / "roles.json").read_text(encoding="utf-8")
    ) == {"version": 2, "roles": []}
    assert (workspace / "roles" / "assets").is_dir()
    assert any(path == config_path for path in summary.created)


def test_init_workspace_respects_force_for_text_assets(tmp_path):
    config_path = tmp_path / "config.toml"
    workspace = tmp_path / "workspace"

    workspace_init.init_workspace(
        config_path=config_path,
        workspace=workspace,
    )
    config_text = config_path.read_text(encoding="utf-8").replace(
        'max_iterations = 40',
        'max_iterations = 99',
        1,
    )
    config_path.write_text(config_text, encoding="utf-8")

    summary_skip = workspace_init.init_workspace(
        config_path=config_path,
        workspace=workspace,
    )
    assert 'max_iterations = 99' in config_path.read_text(encoding="utf-8")
    assert any(path == config_path for path in summary_skip.skipped)

    summary_force = workspace_init.init_workspace(
        config_path=config_path,
        workspace=workspace,
        force=True,
    )
    assert "[llm]" in config_path.read_text(encoding="utf-8")
    assert any(path == config_path for path in summary_force.overwritten)

