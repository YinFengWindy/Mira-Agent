"""Prepare/publish protocol used by the settings transaction boundary."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

from agent.config_models import Config
from bootstrap.runtime.events import RuntimeEventBus
from bootstrap.runtime.generations import RuntimeCandidate
from bootstrap.tools import build_core_runtime
from bootstrap.channels import start_channels
from bootstrap.runtime.memory import validate_memory_transition
from bootstrap.runtime.construction import prepare_core_runtime
from bootstrap.runtime.channel_barrier import channel_handover_barrier


class RuntimeReloadMixin:
    """Owns configuration publication without restarting the application."""

    @property
    def generation(self) -> int:
        """Returns the active version, or zero before startup."""
        return self._current.generation if self._current is not None else 0

    @property
    def retained_generations(self):
        """Returns active resource owners for cross-generation task inspection."""
        return tuple(generation for generation in self._generations if not generation.closed)

    @property
    def accepting_work(self) -> bool:
        """Reports whether new user operations can be accepted immediately."""
        return self._admission_open.is_set() and not self._shutdown

    def acquire(self):
        """Pins the currently published runtime for one logical operation."""
        if self._current is None or self._shutdown:
            raise RuntimeError("Application runtime is not running")
        return self._current.acquire()

    def pin(self):
        """Retains idle bridge handlers without counting them as accepted work."""
        if self._current is None or self._shutdown:
            raise RuntimeError("Application runtime is not running")
        return self._current.acquire(persistent=True)

    async def wait_for_admission(self) -> None:
        """Defers new operations while a process-global channel identity changes."""
        await self._admission_open.wait()

    async def prepare(self, config: Config) -> RuntimeCandidate:
        """Prepares isolated capabilities while the active runtime stays available."""
        if self._current is None or self._shutdown:
            raise RuntimeError("Application runtime is not running")
        if config == self.config:
            return self._current
        validate_memory_transition(self.config, config, self.workspace)
        snapshot = deepcopy(config)
        core = await prepare_core_runtime(
            snapshot,
            self.workspace,
            self.http_resources,
            builder=build_core_runtime,
            shared=self.core,
            event_bus=RuntimeEventBus(self.event_bus),
            event_outlet=self.event_bus,
            agent_loop_provider=lambda: self._dispatcher,
        )
        candidate = RuntimeCandidate(self.generation + 1, core, snapshot)
        try:
            await core.start()
            self._prepare_background(candidate)
            plugins = core.plugin_manager
            candidate.channel_host = await start_channels(
                snapshot, bus=self.bus, session_manager=self.session_manager,
                push_tool=self.push_tool, http_resources=self.http_resources,
                event_bus=self.event_bus, interrupt_controller=self._dispatcher,
                bot_commands=plugins.telegram_bot_commands if plugins else None,
                plugin_channels=plugins.channels if plugins else None,
                enable_message_channels=self.features.enable_message_channels,
                previous_host=self.channel_host, strict=True,
            )
        except BaseException:
            self._discard_background(candidate)
            await candidate.retire()
            raise
        return candidate

    async def publish(
        self,
        candidate: RuntimeCandidate,
        commit: Callable[[], None] | None = None,
    ) -> None:
        """Commits persistence immediately before publishing the prepared pointer."""
        current = self._current
        if current is None or self._shutdown:
            raise RuntimeError("Application runtime is not running")
        if candidate is self._current:
            if commit is not None:
                commit()
            return
        if candidate.closed or candidate.published or candidate.generation != self.generation + 1:
            raise RuntimeError("Runtime candidate is stale or already consumed")
        def publish_pointer() -> None:
            validate_memory_transition(self.config, candidate.config, self.workspace)
            if commit is not None:
                commit()
            previous = self._current
            candidate.published = True
            self._current = candidate
            self.config = candidate.config
            self._adopt_core(candidate.core)
            self._track_generation(candidate)
            self._publish_background(previous, candidate)
            # No await separates durable commit and pointer publication.
            previous.retired = True
            self._retirements.spawn(
                previous.close_if_idle(),
                name=f"runtime:{previous.generation}:retire",
            )

        if self.channel_host is not None and candidate.channel_host is not None:
            def restore_background() -> None:
                try:
                    self._prepare_background(current)
                    self._publish_background(None, current)
                except BaseException as error:
                    try:
                        self._discard_background(current)
                    except BaseException as cleanup_error:
                        raise BaseExceptionGroup("Background recovery failed", [error, cleanup_error]) from error
                    raise

            async with channel_handover_barrier(
                self.channel_host, candidate, current=current,
                accepted=tuple(self._generations), background_groups=self._background_groups,
                admission=self._admission_open, drain_outbound=self.bus.drain_outbound,
                restore_background=restore_background,
            ) as accepted_generations:
                async def retire_transports() -> None:
                    for generation in accepted_generations:
                        await generation.drained.wait()
                    await self.bus.drain_outbound()

                await self.channel_host.handover(
                    candidate.channel_host, commit=publish_pointer, retire_after=retire_transports,
                )
        else:
            publish_pointer()

    async def discard(self, candidate: RuntimeCandidate) -> None:
        """Closes an unpublished candidate after failed preparation or persistence."""
        if candidate.published:
            return
        self._discard_background(candidate)
        await candidate.retire()

    def _adopt_core(self, core) -> None:
        self.core = core
        self.agent_loop = core.loop
        self.bus = core.bus
        self.tools = core.tools
        self.push_tool = core.push_tool
        self.session_manager = core.session_manager
        self.scheduler = core.scheduler
        self.provider = core.provider
        self.light_provider = core.light_provider
        self.mcp_registry = core.mcp_registry
        self.memory_runtime = core.memory_runtime
        self.presence = core.presence
        self.relationship_runtime = core.relationship_runtime

    def _track_generation(self, candidate: RuntimeCandidate) -> None:
        self._generations.append(candidate)
        candidate.on_closed = self._generation_closed

    def _generation_closed(self, candidate: RuntimeCandidate) -> None:
        if candidate is not self._current and candidate in self._generations:
            self._generations.remove(candidate)
        self._background_groups.pop(candidate, None)
