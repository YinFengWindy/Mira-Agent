from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.lifecycle.types import AfterStepCtx
from plugins.context_pressure.plugin import (
    ContextPressureStopModule,
    _CONTEXT_PRESSURE_STOP_THRESHOLD_TOKENS,
    setup,
)


def _after_step_ctx(*, has_more: bool, tokens: int) -> AfterStepCtx:
    return AfterStepCtx(
        session_key="cli:1",
        channel="cli",
        chat_id="1",
        iteration=1,
        context_tokens_estimate=tokens,
        tools_called=(),
        partial_reply="",
        tools_used_so_far=(),
        tool_chain_partial=(),
        partial_thinking=None,
        has_more=has_more,
    )


@pytest.mark.asyncio
async def test_requests_early_stop_when_pressure_exceeds_threshold() -> None:
    module = ContextPressureStopModule()
    ctx = _after_step_ctx(has_more=True, tokens=_CONTEXT_PRESSURE_STOP_THRESHOLD_TOKENS + 1)
    frame = SimpleNamespace(slots={"step:ctx": ctx})

    result = await module.run(frame)

    assert result.slots["step:early_stop_reason"] == "context_pressure"
    assert (
        result.slots["step:telemetry:context_pressure_tokens"]
        == _CONTEXT_PRESSURE_STOP_THRESHOLD_TOKENS + 1
    )
    assert (
        result.slots["step:telemetry:context_pressure_threshold"]
        == _CONTEXT_PRESSURE_STOP_THRESHOLD_TOKENS
    )


@pytest.mark.asyncio
async def test_no_early_stop_below_threshold() -> None:
    module = ContextPressureStopModule()
    ctx = _after_step_ctx(has_more=True, tokens=_CONTEXT_PRESSURE_STOP_THRESHOLD_TOKENS)
    frame = SimpleNamespace(slots={"step:ctx": ctx})

    result = await module.run(frame)

    assert "step:early_stop_reason" not in result.slots


@pytest.mark.asyncio
async def test_no_early_stop_when_no_more_steps() -> None:
    module = ContextPressureStopModule()
    ctx = _after_step_ctx(has_more=False, tokens=_CONTEXT_PRESSURE_STOP_THRESHOLD_TOKENS + 1)
    frame = SimpleNamespace(slots={"step:ctx": ctx})

    result = await module.run(frame)

    assert "step:early_stop_reason" not in result.slots


@pytest.mark.asyncio
async def test_setup_contributes_after_step_module() -> None:
    """setup(ctx) 必须与旧 ContextPressurePlugin.after_step_modules() 等价。"""

    class _FakeLifecycle:
        def __init__(self) -> None:
            self.contributed: dict[str, list[object]] = {}

        def contribute(self, slot: str, modules: list[object]) -> None:
            self.contributed[slot] = modules

    class _FakeCtx:
        def __init__(self) -> None:
            self.lifecycle = _FakeLifecycle()

    ctx = _FakeCtx()
    await setup(ctx)

    assert [type(m).__name__ for m in ctx.lifecycle.contributed["after_step"]] == [
        "ContextPressureStopModule"
    ]
