import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bootstrap.runtime.generations import RuntimeCandidate
from core.common.runtime_scope import bind_runtime, current_runtime_lease
from core.common.runtime_tasks import create_runtime_task


def version():
    return RuntimeCandidate(7, SimpleNamespace(stop=AsyncMock(), memory_runtime=SimpleNamespace(aclose=AsyncMock())), SimpleNamespace())


@pytest.mark.asyncio
async def test_detached_child_chain_keeps_original_version_until_last_child_finishes():
    generation = version()
    parent = generation.acquire()
    child_started = asyncio.Event()
    finish_child = asyncio.Event()
    children = []
    observed = []

    async def child():
        observed.append(current_runtime_lease().generation)
        child_started.set()
        await finish_child.wait()

    async def scene():
        observed.append(current_runtime_lease().generation)
        children.append(create_runtime_task(child(), name="cg"))

    with bind_runtime(parent):
        task = create_runtime_task(scene(), name="scene")
    await parent.release()
    await generation.retire()
    await child_started.wait()
    await task
    assert not generation.closed
    finish_child.set()
    await asyncio.gather(*children)
    await asyncio.wait_for(generation.drained.wait(), timeout=1)
    assert observed == [7, 7]
    generation.core.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_before_task_starts_releases_its_retained_version():
    generation = version()
    parent = generation.acquire()
    operation = AsyncMock()
    with bind_runtime(parent):
        task = create_runtime_task(operation(), name="cancel-before-start")
    task.cancel()
    await parent.release()
    await generation.retire()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.wait_for(generation.drained.wait(), timeout=1)
    operation.assert_not_awaited()
