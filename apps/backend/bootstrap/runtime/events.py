"""Generation-local handlers with one stable external event outlet."""

import asyncio
from contextvars import Context, copy_context
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bus.event_bus import EventBus
from core.common.runtime_scope import bind_runtime, current_runtime_lease
from core.common.runtime_tasks import release_lease_in_background

if TYPE_CHECKING:
    from bootstrap.runtime.generations import RuntimeLease


@dataclass
class _QueuedEvent:
    event: object
    context: Context
    lease: "RuntimeLease | None"


class RuntimeEventBus(EventBus):
    """Keeps plugin handlers private while forwarding events to bridge observers."""

    def __init__(self, outlet: EventBus) -> None:
        super().__init__()
        self._outlet = outlet

    async def emit(self, event):
        """Runs this generation's interceptors before external interceptors."""
        return await self._outlet.emit(await super().emit(event))

    async def observe(self, event) -> None:
        """Notifies local and external observers exactly once."""
        await super().observe(event)
        await self._outlet.observe(event)

    async def fanout(self, event) -> None:
        """Drains queued generation work before publishing externally."""
        if isinstance(event, _QueuedEvent):

            async def deliver():
                if event.lease is None:
                    await self._fanout_event(event.event)
                else:
                    with bind_runtime(event.lease):
                        await self._fanout_event(event.event)

            task = asyncio.create_task(deliver(), context=event.context)
            if event.lease is not None:
                # A separate release task lets the queue mark its item complete
                # before generation cleanup waits for that queue to drain.
                task.add_done_callback(
                    lambda _: release_lease_in_background(event.lease)
                )
            await task
            return
        await self._fanout_event(event)

    async def _fanout_event(self, event) -> None:
        await super().fanout(event)
        await self._outlet.fanout(event)

    def enqueue(self, event: object) -> None:
        """Captures each producer's model snapshot and pins its runtime independently."""
        if self._closed:
            raise RuntimeError("Cannot enqueue work on a closed runtime event bus")
        parent = current_runtime_lease()
        lease = parent.retain() if parent is not None else None
        super().enqueue(_QueuedEvent(event, copy_context(), lease))
