"""Retained ownership for detached work spawned by runtime capabilities."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

from core.common.runtime_scope import bind_runtime, current_runtime_lease

logger = logging.getLogger(__name__)
T = TypeVar("T")


def create_runtime_task(
    operation: Coroutine[Any, Any, T], *, name: str
) -> asyncio.Task[T]:
    """Pins the caller's generation until this task and any retained children finish."""
    parent = current_runtime_lease()
    if parent is None:
        return asyncio.create_task(operation, name=name)
    lease = parent.retain()

    async def run():
        with bind_runtime(lease):
            return await operation

    task = asyncio.create_task(run(), name=name)

    def finished(completed):
        # Cancellation before the wrapper's first step must still close its input
        # coroutine and release ownership. Release outside the owned task so its
        # generation can drain task registries without waiting on itself.
        operation.close()
        release_lease_in_background(lease, name=f"{name}:release")

    task.add_done_callback(finished)
    return task


def release_lease_in_background(
    lease, *, name: str = "runtime-lease-release"
) -> asyncio.Task[None]:
    """Releases generation ownership outside the owned task, logging any failure."""
    task = asyncio.create_task(lease.release(), name=name)
    task.add_done_callback(_report_release_failure)
    return task


def _report_release_failure(task: asyncio.Task[None]) -> None:
    if not task.cancelled() and (error := task.exception()) is not None:
        logger.error(
            "Detached runtime task cleanup failed",
            exc_info=(type(error), error, error.__traceback__),
        )
