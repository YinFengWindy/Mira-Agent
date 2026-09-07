from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from infra.channels.contract import Channel, ChannelContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChannelFailure:
    """Describes a channel that could not be constructed or started."""

    channel: str
    phase: str
    error_type: str
    message: str


class ChannelHandoverError(RuntimeError):
    """A failed channel switch, including any connections that could not recover."""

    def __init__(self, failure: ChannelFailure, degraded: list[ChannelFailure]) -> None:
        self.failure = failure
        self.degraded = degraded
        super().__init__(f"Channel {failure.channel} {failure.phase} failed: {failure.message}")

    def to_details(self):
        """Returns actionable connection status without reporting successful rollback."""
        from dataclasses import asdict
        return {"failure": asdict(self.failure), "degraded": [asdict(item) for item in self.degraded]}


class ChannelHost:
    def __init__(
        self,
        ctx_factory: Callable[[Channel], ChannelContext],
        *,
        transport_lock: asyncio.Lock | None = None,
    ) -> None:
        self._ctx_factory = ctx_factory
        self._channels: list[Channel] = []
        self._failures: list[ChannelFailure] = []
        self._configurations: dict[str, object] = {}
        self._transport_lock = transport_lock or asyncio.Lock()
        self._retired_transports: dict[str, Channel] = {}
        self._retirement_tasks: set[asyncio.Task[None]] = set()

    def add(self, channel: Channel, *, configuration: object = None) -> None:
        """Registers one candidate without starting it or binding subscribers."""
        if any(item.name == channel.name for item in self._channels):
            raise ValueError(f"Duplicate channel name: {channel.name}")
        self._channels.append(channel)
        self._configurations[channel.name] = configuration

    def reusable(self, name: str, configuration: object) -> Channel | None:
        """Returns an existing connection when its effective configuration is unchanged."""
        if self._configurations.get(name) != configuration:
            return None
        return next((channel for channel in self._channels if channel.name == name), None)

    def requires_exclusive_handover(self, candidate: ChannelHost) -> bool:
        """Requires accepted work to drain before a channel name changes connection."""
        existing = {channel.name: channel for channel in self._channels}
        existing.update(self._retired_transports)
        return any(
            channel.name in existing and existing[channel.name] is not channel
            for channel in candidate.channels
        )

    def pause_intake(self) -> None:
        """Closes channel admission while existing replies drain on their credentials."""
        paused = []
        try:
            for channel in self._channels:
                channel.pause_intake()
                paused.append(channel)
        except BaseException:
            for channel in reversed(paused):
                channel.resume_intake()
            raise

    def resume_intake(self) -> None:
        """Reopens the currently published connections after a replacement attempt."""
        for channel in self._channels:
            channel.resume_intake()

    async def handover(
        self, candidate: ChannelHost, *, commit: Callable[[], None] | None = None,
        retire_after: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Switches changed connections under the send barrier and rolls back failures."""
        from bootstrap.channel_handover import handover_channels
        async with self._transport_lock:
            parked = await handover_channels(self, candidate, commit=commit, retain_removed=retire_after is not None)
            if parked and retire_after is not None:
                for channel in parked:
                    self._retired_transports[channel.name] = channel
                    self._ctx_factory(channel).push_tool.retire_channel(channel.name)
                task = asyncio.create_task(self._retire_transports(parked, retire_after))
                self._retirement_tasks.add(task)

    async def _retire_transports(self, channels, ready) -> None:
        await ready()
        async with self._transport_lock:
            for channel in channels:
                if self._retired_transports.get(channel.name) is not channel:
                    continue
                try:
                    await channel.stop()
                except Exception as error:
                    self.record_failure(channel.name, phase="retire", error=error)
                    raise
                self._retired_transports.pop(channel.name, None)

    def record_failure(self, channel: str, *, phase: str, error: BaseException) -> None:
        """Records a channel failure while allowing independent channels to proceed."""

        self._failures.append(
            ChannelFailure(
                channel=str(channel),
                phase=str(phase),
                error_type=type(error).__name__,
                message=str(error),
            )
        )

    async def start_all(self) -> None:
        for channel in self._channels:
            try:
                await channel.start(self._ctx_factory(channel))
                logger.info("渠道已启动: %s", channel.name)
            except Exception as e:
                self.record_failure(channel.name, phase="start", error=e)
                logger.error("渠道启动失败 %s: %s", channel.name, e)

    async def stop_all(self) -> None:
        for task in self._retirement_tasks:
            task.cancel()
        if self._retirement_tasks:
            await asyncio.gather(*self._retirement_tasks, return_exceptions=True)
        for channel in reversed([*self._channels, *self._retired_transports.values()]):
            try:
                await channel.stop()
            except Exception as e:
                logger.warning("渠道停止失败 %s: %s", channel.name, e)

    @property
    def channels(self) -> list[Channel]:
        return list(self._channels)

    @property
    def failures(self) -> list[ChannelFailure]:
        """Returns a snapshot of channel construction/start failures."""

        return list(self._failures)
