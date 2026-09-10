from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.lifecycle.types import AfterStepCtx
from agent.plugin_host import HostServices, PluginKernel
from bus.event_bus import EventBus
from plugins.context_pressure.backend.plugin import (
    ContextPressureStopModule,
    _CONTEXT_PRESSURE_STOP_THRESHOLD_TOKENS,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


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
async def test_setup_contributes_after_step_module_via_kernel(tmp_path: Path) -> None:
    """setup(ctx) 必须与旧 ContextPressurePlugin.after_step_modules() 等价。

    用真实 PluginKernel 装配真实插件目录来验证，而不是自造 fake capability——
    fake 与真实 capability 契约脱钩，capability 改坏也不会让测试变红（#182 评审）。
    """
    root = tmp_path / "plugins"
    root.mkdir()
    shutil.copytree(REPO_ROOT / "plugins" / "context_pressure", root / "context_pressure")
    kernel = PluginKernel([root], services=HostServices(event_bus=EventBus()))
    await kernel.load_all()

    assert [type(m).__name__ for m in kernel.after_step_modules] == [
        "ContextPressureStopModule"
    ]

    # 卸载后贡献必须整体撤回，证明 phase 槽位真正挂在插件作用域上
    _ = await kernel.unload("context_pressure")
    assert kernel.after_step_modules == []
