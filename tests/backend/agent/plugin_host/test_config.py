"""Plugin config grants independent snapshots and explicit missing attributes."""

import pytest
from agent.plugin_host.config import PluginConfig


def test_config_copies_values_and_returns_independent_top_level_snapshot():
    values = {"token": "old"}
    config = PluginConfig(values)
    values["token"] = "new"
    assert config.token == "old"
    snapshot = config.as_dict()
    snapshot["token"] = "modified"
    assert config.get("token") == "old"
    assert config.get("missing", 3) == 3
    with pytest.raises(AttributeError):
        _ = config.missing
