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

    ``ctx.effect("controller_terminate", ...)`` 必须先于三个 ``ctx.events.on``
    登记：``EffectScope.dispose_all`` 按 LIFO 逆序处置，先登记的后处置。若顺序
    颠倒（先 events.on 再 effect），卸载时会先跑 controller.terminate() 再撤销
    事件订阅——``SceneAwarenessController.terminate()`` 对 in-flight 任务是
    "snapshot tasks -> cancel -> await gather -> clear()"，await 期间订阅仍然
    生效，此时若有 ProactiveMessageCommitted 落地，
    ``schedule_proactive_turn`` 会把一个新任务塞进 ``_tasks``（不在 snapshot
    里，因此不会被 cancel），terminate() 末尾的 ``clear()`` 随即丢弃对它的
    唯一引用——任务泄漏，再也无法取消或等待。先登记 effect（=最后处置，
    最先执行）能保证 controller.terminate() 在三个订阅撤销之前跑，与旧
    ``terminate()`` 手写的 "先 event_bus.off，再 await controller.terminate()"
    顺序等价（#183 复审）。
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

    # 登记顺序刻意在三个事件订阅之前：见上方文档。
    ctx.effect("controller_terminate", controller.terminate)
    ctx.events.on(BeforeTurnCtx, _capture_passive_turn)
    ctx.events.on(AfterTurnCtx, _schedule_passive_turn)
    ctx.events.on(ProactiveMessageCommitted, _handle_proactive_message)
