from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from agent.config_models import Config, ModelRegistration
from bootstrap.app import AppRuntime, RuntimeFeatures


@pytest.mark.asyncio
async def test_empty_application_hot_reload_preserves_shared_state_and_old_lease(tmp_path, monkeypatch):
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda _: [])
    config = Config(provider="", model="", api_key="", model_registrations=[], memory_optimizer_enabled=False)
    app = AppRuntime(config, tmp_path, features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False))
    await app.start()
    lease = app.acquire()
    original = app.core
    try:
        prepared = await app.prepare(replace(config, max_tokens=2048))
        assert app.generation == 1
        assert prepared.core.loop is not original.loop
        assert prepared.core.session_manager is original.session_manager
        assert prepared.core.bus is original.bus
        commits = []
        await app.publish(prepared, commit=lambda: commits.append(app.generation))
        assert commits == [1]
        assert app.generation == 2
        assert app.agent_loop.max_iterations == config.max_iterations
        assert lease.core is original
        assert not original.event_bus._closed
        await lease.release()
        assert original.event_bus._closed
    finally:
        await lease.release()
        await app.shutdown()


@pytest.mark.asyncio
async def test_persistence_failure_keeps_live_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda _: [])
    config = Config(provider="", model="", api_key="", model_registrations=[], memory_optimizer_enabled=False)
    app = AppRuntime(config, tmp_path, features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False))
    await app.start()
    original = app.core
    prepared = await app.prepare(replace(config, max_tokens=2048))

    def fail():
        raise OSError("disk full")

    try:
        with pytest.raises(OSError, match="disk full"):
            await app.publish(prepared, commit=fail)
        assert app.generation == 1
        assert app.core is original
        await app.discard(prepared)
        assert prepared.closed
        assert not original.event_bus._closed
    finally:
        await app.shutdown()


@pytest.mark.asyncio
async def test_partial_candidate_construction_closes_new_provider_and_preserves_live_core(tmp_path, monkeypatch):
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda _: [])
    config = Config(provider="", model="", api_key="", model_registrations=[], memory_optimizer_enabled=False)
    app = AppRuntime(config, tmp_path, features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False))
    await app.start()
    original = app.core
    allocated = []

    class Provider:
        def __init__(self, **kwargs):
            self.aclose = AsyncMock()
            allocated.append(self)

    def fail(**kwargs):
        raise ValueError("context assembly failed")

    monkeypatch.setattr("bootstrap.providers.LLMProvider", Provider)
    monkeypatch.setattr("bootstrap.tools._build_loop_deps", fail)
    changed = replace(config, provider="openai", model="configured", api_key="key", model_registrations=[
        ModelRegistration(id="model", provider="openai", model="configured", api_key="key", base_url=""),
    ])
    try:
        with pytest.raises(ValueError, match="context assembly failed"):
            await app.prepare(changed)
        assert len(allocated) == 1
        allocated[0].aclose.assert_awaited_once()
        assert app.core is original
        assert app.generation == 1
        assert not original.event_bus._closed
    finally:
        await app.shutdown()
