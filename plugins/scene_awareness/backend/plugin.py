from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agent.lifecycle.types import AfterTurnCtx, BeforeTurnCtx
from bus.events_lifecycle import ProactiveMessageCommitted
from core.roles.store import RoleStore
from plugins.scene_awareness.backend.controller import SceneAwarenessController

if TYPE_CHECKING:
    from agent.plugin_host.runtime_context import PluginRuntimeContext

logger = logging.getLogger(__name__)


async def setup(ctx: "PluginRuntimeContext") -> None:
    """装配 scene_awareness：观察完成的角色回合并发布共享场景决策。

    ``ctx.effect`` 登记 ``controller.terminate()`` 作为自定义副作用，卸载时
    取消并等待所有进行中的场景观察后台任务，对齐旧 ``terminate()`` 的收尾。
    """
    workspace = ctx.workspace
    if workspace is None:
        raise RuntimeError("场景观察插件需要 workspace")
    controller = SceneAwarenessController(
        role_store=RoleStore(workspace),
        session_manager=ctx.session_manager,
        event_bus=ctx.events,
        kv_store=ctx.kv,
        light_provider=ctx.light_provider,
        light_model=ctx.light_model,
    )
    if ctx.light_provider is None or not ctx.light_model.strip():
        logger.warning("场景观察缺少 light_model provider，后台判定已禁用")

    async def _capture_passive_turn(event: BeforeTurnCtx) -> BeforeTurnCtx:
        """Capture the passive turn before reasoning mutates its context."""
        controller.capture_passive_turn(event)
        return event

    async def _schedule_passive_turn(event: AfterTurnCtx) -> None:
        """Schedule observation after a passive text turn completes."""
        controller.schedule_passive_turn(event)

    def _handle_proactive_message(event: ProactiveMessageCommitted) -> None:
        controller.schedule_proactive_turn(event)

    ctx.events.on(BeforeTurnCtx, _capture_passive_turn)
    ctx.events.on(AfterTurnCtx, _schedule_passive_turn)
    ctx.events.on(ProactiveMessageCommitted, _handle_proactive_message)
    ctx.effect("controller_terminate", controller.terminate)
