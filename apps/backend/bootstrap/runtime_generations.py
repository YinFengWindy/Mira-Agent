"""Reference-counted runtime versions; publication never cancels their work."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bootstrap.channel_host import ChannelHost
    from agent.config_models import Config
    from bootstrap.tools import CoreRuntime


@dataclass(eq=False)
class RuntimeCandidate:
    """Owns prepared resources until publication or explicit discard."""

    generation: int
    core: CoreRuntime
    config: Config
    references: int = 0
    persistent_references: int = 0
    retired: bool = False
    published: bool = False
    closed: bool = False
    drained: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)
    on_closed: Callable[[RuntimeCandidate], None] | None = field(default=None, repr=False)
    _close_task: asyncio.Task[None] | None = field(default=None, init=False, repr=False)
    channel_host: ChannelHost | None = None
    _work_changed: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)

    def acquire(self, *, persistent: bool = False):
        """Pins this exact version for a request or a detached child operation."""
        if self.closed or (self.retired and not self.references):
            raise RuntimeError("Runtime generation has already retired")
        self.references += 1
        if persistent:
            self.persistent_references += 1
        return RuntimeLease(self, persistent=persistent)

    async def wait_for_work(self) -> None:
        """Waits for accepted operations, excluding idle bridge handler ownership."""
        while self.references > self.persistent_references:
            self._work_changed.clear()
            await self._work_changed.wait()

    async def retire(self) -> None:
        """Stops accepting work and closes only after the final lease exits."""
        self.retired = True
        await self.close_if_idle()

    async def close_if_idle(self) -> None:
        """Releases owned resources exactly once when no task retains them."""
        if self._close_task is not None:
            await asyncio.shield(self._close_task)
            return
        if not self.retired or self.references or self.closed:
            return
        self.closed = True
        self._close_task = asyncio.create_task(self._close_resources())
        await asyncio.shield(self._close_task)

    async def _close_resources(self) -> None:
        try:
            try:
                await self.core.stop()
            finally:
                await self.core.memory_runtime.aclose()
        finally:
            self.drained.set()
            if self.on_closed is not None:
                self.on_closed(self)
                self.on_closed = None


class RuntimeLease:
    """A releasable reference to the immutable resources chosen at task start."""

    def __init__(self, candidate: RuntimeCandidate, *, persistent: bool = False) -> None:
        self._candidate = candidate
        self._released = False
        self._persistent = persistent

    @property
    def core(self) -> CoreRuntime:
        """Returns the retained core."""
        return self._candidate.core

    @property
    def config(self) -> Config:
        """Returns the retained configuration."""
        return self._candidate.config

    @property
    def generation(self) -> int:
        """Returns the retained generation identifier."""
        return self._candidate.generation

    def retain(self):
        """Pins the same version for child work that can outlive its parent."""
        if self._released:
            raise RuntimeError("Cannot retain a released runtime lease")
        return self._candidate.acquire()

    async def release(self) -> None:
        """Releases ownership without cancelling any other version's work."""
        if self._released:
            return
        self._released = True
        self._candidate.references -= 1
        if self._persistent:
            self._candidate.persistent_references -= 1
        self._candidate._work_changed.set()
        await self._candidate.close_if_idle()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self.release()
