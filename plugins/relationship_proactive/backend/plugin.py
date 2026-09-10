"""Official relationship-driven admission policies for proactive turns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent.core.proactive_turn.gates import (
    ProactiveGateAdapter,
    ProactiveGateCompletion,
    ProactiveGateContext,
    ProactiveGateDecision,
    ProactiveMode,
)
from bus.events_lifecycle import SceneObservationCommitted
from core.roles.relationship_runtime import RoleRelationshipRuntimeService

if TYPE_CHECKING:
    from agent.plugin_host.runtime_context import PluginRuntimeContext


class _SceneFollowupGate(ProactiveGateAdapter):
    name = "relationship.scene_followup"
    priority = 100

    def __init__(self, runtime: RoleRelationshipRuntimeService) -> None:
        self._runtime = runtime

    def evaluate(self, ctx: ProactiveGateContext) -> ProactiveGateDecision:
        should_follow_up, metadata = self._runtime.should_trigger_scene_followup(
            ctx.session_key,
            ctx.now_utc,
        )
        if not should_follow_up:
            return ProactiveGateDecision.continue_()
        return ProactiveGateDecision.activate(
            ProactiveMode.SCENE_FOLLOWUP,
            reason="scene_followup",
            metadata=metadata,
        )

    def finalize(self, completion: ProactiveGateCompletion) -> None:
        if completion.outcome == "delivered":
            self._runtime.handle_scene_followup_sent(
                completion.session_key,
                completion.occurred_at,
            )
            return
        self._runtime.close_scene_followup(completion.session_key)


class RelationshipLonelinessGate(ProactiveGateAdapter):
    """Adapts relationship loneliness decisions to the proactive gate contract."""

    name = "relationship.loneliness"
    priority = 0

    def __init__(self, runtime: RoleRelationshipRuntimeService) -> None:
        self._runtime = runtime

    def evaluate(self, ctx: ProactiveGateContext) -> ProactiveGateDecision:
        should_trigger, metadata = self._runtime.should_trigger_proactive(
            ctx.session_key,
            ctx.now_utc,
        )
        if not should_trigger:
            return ProactiveGateDecision.block(
                str(metadata.get("reason") or "loneliness"),
                metadata=metadata,
            )
        return ProactiveGateDecision.activate(
            ProactiveMode.RELATIONSHIP_FALLBACK,
            reason="loneliness",
            metadata=metadata,
        )


async def setup(ctx: "PluginRuntimeContext") -> None:
    """装配 relationship_proactive：贡献主动 tick 准入 gate 并订阅场景决策事件。

    ``ctx.relationship_runtime`` 在同一次 kernel generation 内固定不变（由
    bootstrap 构造 ``HostServices`` 时一次性注入），因此是否贡献 gate 只需在
    装配时判定一次，与旧 ``proactive_gates()`` 每次调用时动态判定 None 的效果
    等价。
    """
    runtime = ctx.relationship_runtime
    if runtime is None:
        return

    def _handle_scene_observation(event: SceneObservationCommitted) -> None:
        runtime.apply_scene_decision(
            event.session_key,
            event.transition,
            event.scene_key,
        )

    ctx.events.on(SceneObservationCommitted, _handle_scene_observation)
    ctx.proactive_gates.add(_SceneFollowupGate(runtime))
    ctx.proactive_gates.add(RelationshipLonelinessGate(runtime))
