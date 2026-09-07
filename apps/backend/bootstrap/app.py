from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from agent.config_models import Config
from bootstrap.channel_host import ChannelHost
from bootstrap.channels import start_channels
from bootstrap.tools import CoreRuntime, build_core_runtime
from bootstrap.runtime.dispatcher import RuntimeDispatcher
from bootstrap.runtime.events import RuntimeEventBus
from bootstrap.runtime.generations import RuntimeCandidate
from bootstrap.runtime.reload import RuntimeReloadMixin
from bootstrap.runtime.background import RuntimeBackgroundMixin
from bootstrap.runtime.shutdown import RuntimeShutdownMixin
from bootstrap.runtime.construction import prepare_core_runtime
from bus.event_bus import EventBus
from core.common.workspace import resolve_default_workspace
from core.roles import (
    LonelinessHeartbeatLoop,
)
from core.common.task_collector import TaskCollector
from core.net.http import (
    SharedHttpResources,
    configure_default_shared_http_resources,
)

def configure_logging_stream(stream) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        stream=stream,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


configure_logging_stream(sys.stderr)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeFeatures:
    enable_message_channels: bool = True
    enable_proactive: bool = True


SERVICE_RUNTIME_FEATURES = RuntimeFeatures()
DESKTOP_RUNTIME_FEATURES = RuntimeFeatures(
    enable_message_channels=True,
)


class AppRuntime(RuntimeReloadMixin, RuntimeBackgroundMixin, RuntimeShutdownMixin):
    def __init__(
        self,
        config: Config,
        workspace: Path,
        *,
        features: RuntimeFeatures = SERVICE_RUNTIME_FEATURES,
    ) -> None:
        self.config = config
        self.workspace = workspace
        self.features = features
        self.http_resources = SharedHttpResources()
        self.channel_host: ChannelHost | None = None
        self.core: CoreRuntime | None = None
        self.agent_loop = None
        self.bus = None
        self.event_bus: EventBus | None = None
        self.tools = None
        self.push_tool = None
        self.session_manager = None
        self.scheduler = None
        self.provider = None
        self.light_provider = None
        self.mcp_registry = None
        self.memory_runtime = None
        self.presence = None
        self.relationship_runtime = None
        self.proactive_loops = {}
        self._background_tasks: list[asyncio.Task[None]] = []
        self._memory_optimizer = None
        self._shutdown = False
        self._started = False
        self._current: RuntimeCandidate | None = None
        self._generations: list[RuntimeCandidate] = []
        self._dispatcher = RuntimeDispatcher(self)
        self._background_groups = {}
        self._retirements = TaskCollector("Retired runtime cleanup")
        self._cleanup_errors: list[Exception] = []
        self._admission_open = asyncio.Event()
        self._admission_open.set()

    async def start(self) -> None:
        if self._started:
            return
        configure_default_shared_http_resources(self.http_resources)
        try:
            self.event_bus = EventBus()
            self.core = await prepare_core_runtime(
                self.config,
                self.workspace,
                self.http_resources,
                builder=build_core_runtime,
                event_bus=RuntimeEventBus(self.event_bus),
                event_outlet=self.event_bus,
                agent_loop_provider=lambda: self._dispatcher,
            )
            self._adopt_core(self.core)
            event_bus = self.event_bus
            await self.core.start()
            self._current = RuntimeCandidate(1, self.core, self.config, published=True)
            self._track_generation(self._current)
            self.bus.bind_runtime_admission(self.acquire)

            plugin_manager = getattr(self.core, "plugin_manager", None)
            self.channel_host = await start_channels(
                self.config,
                bus=self.core.bus,
                session_manager=self.core.session_manager,
                push_tool=self.core.push_tool,
                http_resources=self.http_resources,
                event_bus=event_bus,
                bot_commands=(
                    plugin_manager.telegram_bot_commands
                    if plugin_manager
                    else None
                ),
                interrupt_controller=self._dispatcher,
                plugin_channels=plugin_manager.channels if plugin_manager else None,
                enable_message_channels=self.features.enable_message_channels,
            )
            await self.channel_host.start_all()

            self._background_tasks = [
                asyncio.create_task(self._dispatcher.run(), name="agent_loop"),
                asyncio.create_task(
                    self.bus.dispatch_outbound(),
                    name="bus_dispatch_outbound",
                ),
                asyncio.create_task(self.scheduler.run(), name="scheduler"),
            ]
            self._prepare_background(self._current)
            self._publish_background(None, self._current)
            if self.relationship_runtime is not None:
                loneliness_loop = LonelinessHeartbeatLoop(
                    self.relationship_runtime,
                    role_store=self.core.relationship_runtime.role_store,
                )
                self._background_tasks.extend(
                    [
                        asyncio.create_task(
                            loneliness_loop.run(),
                            name="loneliness_heartbeat_loop",
                        ),
                    ]
                )
            self._started = True
        except Exception:
            await self.shutdown()
            raise

    async def run(self) -> None:
        try:
            await self.start()
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks)
        finally:
            await self.shutdown()



def build_app_runtime(
    config: Config,
    workspace: Path | None = None,
    *,
    features: RuntimeFeatures = SERVICE_RUNTIME_FEATURES,
) -> AppRuntime:
    return AppRuntime(
        config,
        workspace or resolve_default_workspace(),
        features=features,
    )
