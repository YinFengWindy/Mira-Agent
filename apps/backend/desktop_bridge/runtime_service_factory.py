"""Assembly of the desktop handlers for one runtime generation."""

from __future__ import annotations

from bootstrap.tools import CoreRuntime
from core.roles import RoleStore
from desktop_bridge.service import DesktopBridgeService


def build_desktop_service(runtime: CoreRuntime, role_store: RoleStore, *,
                          activate_transport: bool = True) -> DesktopBridgeService:
    """Captures generation-owned dependencies without starting background work."""
    tools = getattr(runtime, "tools", None)
    spawn = tools.get_tool("spawn") if tools else None
    image = tools.get_tool("generate_image") if tools else None
    return DesktopBridgeService(
        workspace=runtime.session_manager.workspace,
        role_store=role_store,
        session_manager=runtime.session_manager,
        agent_loop=runtime.loop,
        event_bus=runtime.event_bus,
        config=getattr(runtime, "config", None),
        model_resolver=getattr(getattr(runtime, "role_runtime_registry", None), "_model_resolver", None),
        activate_transport=activate_transport,
        push_tool=getattr(runtime, "push_tool", None),
        relationship_runtime=getattr(runtime, "relationship_runtime", None),
        presence=getattr(runtime, "presence", None),
        scheduler=getattr(runtime, "scheduler", None),
        subagent_manager=getattr(spawn, "manager", None),
        memory_optimizer=getattr(runtime, "memory_optimizer", None),
        observation_service=getattr(runtime, "screen_observation", None),
        role_runtime_registry=getattr(runtime, "role_runtime_registry", None),
        image_tool=image,
        memory_engine=getattr(getattr(runtime, "memory_runtime", None), "engine", None),
    )
