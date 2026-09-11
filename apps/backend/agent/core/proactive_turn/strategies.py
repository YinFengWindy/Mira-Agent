"""Core scene-followup and relationship motives; an absent motive never vetoes a tick."""

from __future__ import annotations

from agent.core.proactive_turn.gates import (
    ProactiveGateAdapter,
    ProactiveGateCompletion,
    ProactiveGateContext,
    ProactiveGateDecision,
    ProactiveMode,
)
from core.roles.relationship_runtime import RoleRelationshipRuntimeService


class SceneFollowupStrategy(ProactiveGateAdapter):
    """Offers an eligible pending scene and owns its completion accounting."""

    name = "relationship.scene_followup"
    priority = 100

    def __init__(self, runtime: RoleRelationshipRuntimeService) -> None:
        self._runtime = runtime

    def evaluate(self, ctx: ProactiveGateContext) -> ProactiveGateDecision:
        """Offers only scene followups that are due at this tick."""
        should_follow_up, metadata = self._runtime.should_trigger_scene_followup(
            ctx.session_key,
            ctx.now_utc,
        )
        if not should_follow_up:
            return ProactiveGateDecision.continue_(
                reason=str(metadata.get("reason") or "not_due"), metadata=metadata
            )
        return ProactiveGateDecision.activate(
            ProactiveMode.SCENE_FOLLOWUP,
            reason="scene_followup",
            metadata=metadata,
        )

    def finalize(self, completion: ProactiveGateCompletion) -> None:
        """Advances successful followups or closes rejected scenes."""
        if completion.outcome == "delivered":
            self._runtime.handle_scene_followup_sent(
                completion.session_key,
                completion.occurred_at,
            )
            return
        self._runtime.close_scene_followup(completion.session_key)


class RelationshipStrategy(ProactiveGateAdapter):
    """Offers relationship fallback without vetoing external content or Drift."""

    name = "relationship.loneliness"
    priority = 0

    def __init__(self, runtime: RoleRelationshipRuntimeService) -> None:
        self._runtime = runtime

    def evaluate(self, ctx: ProactiveGateContext) -> ProactiveGateDecision:
        """Preserves relationship-specific misses in the shared diagnostic trace."""
        should_trigger, metadata = self._runtime.should_trigger_proactive(
            ctx.session_key,
            ctx.now_utc,
        )
        if not should_trigger:
            return ProactiveGateDecision.continue_(
                reason=str(metadata.get("reason") or "loneliness"),
                metadata=metadata,
            )
        return ProactiveGateDecision.activate(
            ProactiveMode.RELATIONSHIP_FALLBACK,
            reason="loneliness",
            metadata=metadata,
        )
