"""Quiesces accepted runtime work before replacing process-global channel identity."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bootstrap.app import AppRuntime
    from bootstrap.runtime_generations import RuntimeCandidate


@asynccontextmanager
async def channel_handover_barrier(app: AppRuntime, candidate: RuntimeCandidate):
    """Drains published versions while leaving prepared candidate work untouched."""
    accepted = tuple(app._generations)
    host = app.channel_host
    if not host.requires_exclusive_handover(candidate.channel_host):
        yield accepted
        return

    groups = [app._background_groups[generation] for generation in accepted if generation in app._background_groups]
    current_group = app._background_groups.get(app._current)
    stopped_current = False
    failure: BaseException | None = None
    app._admission_open.clear()
    try:
        # Intake can fail after partially pausing channels, so it belongs inside
        # the same recovery boundary as background drain and durable commit.
        host.pause_intake()
        for group in groups:
            if group is current_group:
                stopped_current = True
            group.stop()
        results = await asyncio.gather(*(group.drain() for group in groups), return_exceptions=True)
        errors = [result for result in results if isinstance(result, BaseException)]
        if errors:
            raise BaseExceptionGroup("Accepted background work failed to drain", errors)
        await asyncio.gather(*(generation.wait_for_work() for generation in accepted))
        await app.bus.drain_outbound()
        yield accepted
    except BaseException as error:
        failure = error
        raise
    finally:
        recovery_errors: list[BaseException] = []
        try:
            if stopped_current and not candidate.published:
                try:
                    app._prepare_background(app._current)
                    app._publish_background(None, app._current)
                except BaseException as error:
                    recovery_errors.append(error)
                    try:
                        app._discard_background(app._current)
                    except BaseException as cleanup_error:
                        recovery_errors.append(cleanup_error)
            if not candidate.published:
                try:
                    host.resume_intake()
                except BaseException as error:
                    recovery_errors.append(error)
        finally:
            app._admission_open.set()
        if recovery_errors:
            if failure is not None:
                recovery_errors.insert(0, failure)
            raise BaseExceptionGroup("Channel handover recovery failed", recovery_errors)
