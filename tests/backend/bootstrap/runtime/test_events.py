import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bootstrap.runtime.events import RuntimeEventBus
from bus.event_bus import EventBus
from bootstrap.runtime.generations import RuntimeCandidate
from core.common.runtime_scope import bind_runtime
from core.roles.model_runtime import RoleModelSnapshot, _current_snapshot


@pytest.mark.asyncio
async def test_generation_events_use_only_local_plugins_and_one_shared_outlet():
    outlet = EventBus()
    old, new = RuntimeEventBus(outlet), RuntimeEventBus(outlet)
    calls = []
    old.on(str, lambda event: calls.append(("old", event)))
    new.on(str, lambda event: calls.append(("new", event)))
    outlet.on(str, lambda event: calls.append(("bridge", event)))
    old.enqueue("first")
    await old.drain()
    await old.aclose()
    await new.observe("second")
    assert calls == [("old", "first"), ("bridge", "first"), ("new", "second"), ("bridge", "second")]
    await new.aclose()
    await outlet.aclose()


@pytest.mark.asyncio
async def test_queued_events_keep_each_turn_model_snapshot_and_lease():
    outlet = EventBus()
    bus = RuntimeEventBus(outlet)
    core = SimpleNamespace(stop=AsyncMock(), memory_runtime=SimpleNamespace(aclose=AsyncMock()))
    version = RuntimeCandidate(1, core, SimpleNamespace(), published=True)
    first = version.acquire()
    second = version.acquire()
    seen = []

    def observe(_):
        seen.append(_current_snapshot.get().model)

    bus.on(str, observe)
    for lease, model in [(first, "original"), (second, "updated")]:
        token = _current_snapshot.set(RoleModelSnapshot("id", None, model, "none", role_id="mira"))
        try:
            with bind_runtime(lease):
                bus.enqueue(model)
        finally:
            _current_snapshot.reset(token)
        await lease.release()
    assert version.references == 2
    await bus.drain()
    assert seen == ["original", "updated"]
    for _ in range(5):
        await asyncio.sleep(0)
    assert version.references == 0
    await bus.aclose()
    await outlet.aclose()
