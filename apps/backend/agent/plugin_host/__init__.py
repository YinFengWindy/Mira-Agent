"""插件内核公共入口：内核、manifest、运行时上下文与 capability 契约。"""

from agent.plugin_host.capabilities import PHASE_SLOTS, PluginContributions
from agent.plugin_host.effects import EffectScope
from agent.plugin_host.events import ScopedEventBus
from agent.plugin_host.handle import PluginHandle, PluginRecord, PluginState
from agent.plugin_host.kernel import HostServices, PluginKernel
from agent.plugin_host.manifest import (
    KNOWN_CAPABILITIES,
    ManifestError,
    PluginManifest,
    load_manifest,
)
from agent.plugin_host.runtime_context import (
    CapabilityNotGranted,
    PluginRuntimeContext,
)
from agent.plugin_host.tool_hooks import PluginToolHook

__all__ = [
    "CapabilityNotGranted",
    "EffectScope",
    "HostServices",
    "KNOWN_CAPABILITIES",
    "ManifestError",
    "PHASE_SLOTS",
    "PluginContributions",
    "PluginHandle",
    "PluginKernel",
    "PluginManifest",
    "PluginRecord",
    "PluginRuntimeContext",
    "PluginState",
    "PluginToolHook",
    "ScopedEventBus",
    "load_manifest",
]
