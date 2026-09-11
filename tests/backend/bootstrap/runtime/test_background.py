import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bootstrap.runtime.background import RuntimeBackground
from bootstrap.runtime.generations import RuntimeCandidate
from core.common.runtime_scope import current_runtime_lease


class WorkLoop:
    def __init__(self):
        self.started = asyncio.Event()
        self.finish = asyncio.Event()
        self.stopped = False
        self.version = None

    async def run(self):
        self.version = current_runtime_lease().generation
        self.started.set()
        await self.finish.wait()

    def stop(self):
        self.stopped = True


def candidate(number):
    core = SimpleNamespace(
        provider=None,
        role_runtime_registry=None,
        stop=AsyncMock(),
        memory_runtime=SimpleNamespace(
            markdown=SimpleNamespace(store=None), aclose=AsyncMock()
        ),
    )
    return RuntimeCandidate(
        number, core, SimpleNamespace(model_registrations=[]), published=True
    )


@pytest.mark.asyncio
async def test_new_background_scheduling_waits_for_accepted_old_work(monkeypatch):
    old_loop, new_loop = WorkLoop(), WorkLoop()
    loops = iter([old_loop, new_loop])

    def build(*args, loop_consumer, **kwargs):
        loop = next(loops)
        loop_consumer(loop)
        return [loop.run()], None

    monkeypatch.setattr(
        "bootstrap.runtime.background.build_memory_optimizer_task", build
    )
    app = SimpleNamespace(features=SimpleNamespace(enable_proactive=False))
    old_version, new_version = candidate(1), candidate(2)
    old_group, new_group = RuntimeBackground(app, old_version), RuntimeBackground(
        app, new_version
    )
    old_group.start()
    await old_loop.started.wait()
    old_group.stop()
    await old_version.retire()
    new_group.start(old_group)
    await asyncio.sleep(0)
    assert not new_loop.started.is_set()
    assert old_loop.stopped
    assert not old_version.closed
    old_loop.finish.set()
    await asyncio.wait_for(new_loop.started.wait(), timeout=1)
    assert (old_loop.version, new_loop.version) == (1, 2)
    assert old_version.drained.is_set()
    new_group.stop()
    new_loop.finish.set()
    await new_group.drain()
    await new_version.retire()


def test_scene_intake_activates_at_publication_even_without_polling_loops(monkeypatch):
    from unittest.mock import Mock

    monkeypatch.setattr(
        "bootstrap.runtime.background.build_memory_optimizer_task",
        lambda *args, **kwargs: ([], None),
    )
    version = candidate(1)
    scene = SimpleNamespace(activate=Mock(), deactivate=Mock())
    version.core.scene_service = scene
    group = RuntimeBackground(
        SimpleNamespace(features=SimpleNamespace(enable_proactive=False)), version
    )
    scene.activate.assert_not_called()
    group.start()
    scene.activate.assert_called_once()
    group.stop()
    # Accepted old turns still emit their AfterTurn on this generation-local bus.
    scene.deactivate.assert_not_called()
