"""Persist motive diagnostics without converting them to global rejections."""

from unittest.mock import MagicMock
from agent.core.proactive_turn.gates import ProactiveGateTraceItem
from agent.core.proactive_turn.tick_logging import record_tick_log_finish
from proactive_v2.context import AgentTickContext


def test_motive_miss_is_logged_without_gate_exit():
    store = MagicMock()
    ctx = AgentTickContext(session_key="role:mira")
    ctx.gate_trace = (
        ProactiveGateTraceItem(
            "relationship.loneliness",
            0,
            "continue",
            "cooldown",
            {"loneliness_value": 80},
            1,
        ),
    )
    record_tick_log_finish(state_store=store, session_key=ctx.session_key, ctx=ctx)
    recorded = store.record_tick_log_finish.call_args.kwargs
    assert recorded["gate_exit"] is None
    assert recorded["gate_name"] == "relationship.loneliness"
    assert recorded["gate_reason"] == "cooldown"
    assert recorded["gate_metadata"] == {"loneliness_value": 80}


def test_explicit_global_denial_wins_over_motive_trace():
    store = MagicMock()
    ctx = AgentTickContext(session_key="role:mira")
    ctx.gate_trace = (
        ProactiveGateTraceItem(
            "relationship.loneliness", 0, "continue", "cooldown", {}, 1
        ),
    )
    record_tick_log_finish(
        state_store=store,
        session_key=ctx.session_key,
        ctx=ctx,
        gate_exit="busy",
        gate_name="global",
        gate_reason="busy",
        gate_metadata={"busy": True},
    )
    recorded = store.record_tick_log_finish.call_args.kwargs
    assert recorded["gate_exit"] == "busy"
    assert recorded["gate_name"] == "global"
    assert recorded["gate_metadata"] == {"busy": True}
