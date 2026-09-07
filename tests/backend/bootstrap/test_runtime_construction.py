from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bootstrap.runtime_construction import prepare_core_runtime, track_build_resource


@pytest.mark.asyncio
async def test_construction_failure_closes_partial_resources_once_in_reverse_order():
    closed = []
    first, second = object(), object()

    def build():
        track_build_resource(first, lambda: closed.append("first"))
        track_build_resource(second, lambda: closed.append("second"))
        track_build_resource(first, lambda: closed.append("duplicate"))
        raise ValueError("invalid memory config")

    with pytest.raises(ValueError, match="invalid memory config"):
        await prepare_core_runtime(builder=build)
    assert closed == ["second", "first"]


@pytest.mark.asyncio
async def test_complete_runtime_takes_ownership_without_closing_resources():
    resource = SimpleNamespace(aclose=AsyncMock())

    def build():
        track_build_resource(resource, resource.aclose)
        return SimpleNamespace(provider=resource)

    runtime = await prepare_core_runtime(builder=build)
    assert runtime.provider is resource
    resource.aclose.assert_not_awaited()


@pytest.mark.asyncio
async def test_default_memory_constructor_failure_closes_open_database(tmp_path, monkeypatch):
    from agent.config_models import Config
    from plugins.default_memory.config import load_default_memory_config
    from plugins.default_memory.engine.lifecycle import DefaultMemoryEngine

    store = SimpleNamespace(close=Mock())
    monkeypatch.setattr("plugins.default_memory.engine.lifecycle.MemoryStore2", lambda *args, **kwargs: store)
    monkeypatch.setattr("plugins.default_memory.engine.lifecycle.Embedder", Mock(side_effect=ValueError("bad embedding")))
    config = Config(provider="", model="", api_key="", model_registrations=[])

    def build():
        return DefaultMemoryEngine(
            config=config, default_config=load_default_memory_config(), workspace=tmp_path,
            provider=None, http_resources=SimpleNamespace(external_default=None),
        )

    with pytest.raises(ValueError, match="bad embedding"):
        await prepare_core_runtime(builder=build)
    store.close.assert_called_once()
