import asyncio

import pytest

from agent.config_models import Config
from bootstrap.app import AppRuntime, RuntimeFeatures
from bus.events import SpawnCompletionItem
from core.common.runtime_scope import bind_runtime


async def start_app(tmp_path, monkeypatch):
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda _: [])
    config = Config(provider="", model="", api_key="", model_registrations=[], memory_optimizer_enabled=False)
    app = AppRuntime(config, tmp_path, features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False))
    await app.start()
    return app


@pytest.mark.asyncio
async def test_shutdown_keeps_http_resources_until_queued_event_lease_drains(tmp_path, monkeypatch):
    app = await start_app(tmp_path, monkeypatch)
    entered, finish = asyncio.Event(), asyncio.Event()

    async def observe(_):
        entered.set()
        await finish.wait()

    app.core.event_bus.on(str, observe)
    lease = app.acquire()
    with bind_runtime(lease):
        app.core.event_bus.enqueue("pending")
    await lease.release()
    await entered.wait()
    shutdown = asyncio.create_task(app.shutdown())
    await asyncio.sleep(0)
    assert not app.http_resources._closed
    assert not shutdown.done()
    finish.set()
    await asyncio.wait_for(shutdown, timeout=2)
    assert app.http_resources._closed
    assert app._current.drained.is_set()


@pytest.mark.asyncio
async def test_shutdown_releases_queued_spawn_completion_lease(tmp_path, monkeypatch):
    app = await start_app(tmp_path, monkeypatch)
    retained = app.acquire()
    await app.bus.publish_inbound(SpawnCompletionItem("desktop", "one", object(), runtime_lease=retained))
    await asyncio.wait_for(app.shutdown(), timeout=2)
    assert app._current.references == 0
    assert app._current.drained.is_set()
