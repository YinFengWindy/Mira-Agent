"""Persistence and failure behavior of the plugin KV capability."""

from pathlib import Path
import pytest
from agent.plugin_host.kv import PluginKVStore


def test_values_survive_reopening_and_preserve_other_keys(tmp_path: Path):
    path = tmp_path / "data/kv.json"
    store = PluginKVStore(path)
    assert store.get("missing", "default") == "default"
    store.set("scene", {"name": "夜空", "ids": [1, 2]})
    assert store.increment("turn", 4) == 4
    reopened = PluginKVStore(path)
    assert reopened.increment("turn", -1) == 3
    assert store.get("turn") == 3
    assert reopened.get("scene") == {"name": "夜空", "ids": [1, 2]}


def test_invalid_persisted_data_is_not_silently_reset(tmp_path: Path):
    path = tmp_path / "kv.json"
    path.write_text("broken", encoding="utf-8")
    with pytest.raises(ValueError):
        PluginKVStore(path).set("key", "value")
    assert path.read_text(encoding="utf-8") == "broken"
