from dataclasses import replace

import pytest

from agent.config_models import Config
from bootstrap.runtime.memory import MemoryStorageIncompatibleError, validate_memory_transition


def test_existing_vector_storage_allows_connection_changes_but_rejects_new_vector_space(tmp_path, monkeypatch):
    path = tmp_path / "memory.db"
    path.touch()
    monkeypatch.setattr("plugins.default_memory.config.resolve_memory_db_path", lambda **_: path)
    original = Config(provider="", model="", api_key="", model_registrations=[])
    original.memory.enabled = True
    credentials = replace(original, memory=replace(original.memory, embedding=replace(original.memory.embedding, api_key="changed")))
    validate_memory_transition(original, credentials, tmp_path)
    incompatible = replace(original, memory=replace(original.memory, embedding=replace(original.memory.embedding, output_dimensionality=128)))
    with pytest.raises(MemoryStorageIncompatibleError) as failure:
        validate_memory_transition(original, incompatible, tmp_path)
    assert failure.value.to_details()["reason"] == "embedding_migration_required"


def test_new_storage_can_select_its_initial_embedding_space(tmp_path, monkeypatch):
    monkeypatch.setattr("plugins.default_memory.config.resolve_memory_db_path", lambda **_: tmp_path / "missing.db")
    original = Config(provider="", model="", api_key="", model_registrations=[])
    changed = replace(original, memory=replace(original.memory, enabled=True, embedding=replace(original.memory.embedding, model="new-embedding")))
    validate_memory_transition(original, changed, tmp_path)
