from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent.core.proactive_turn.gates import (
    ProactiveGateChain,
    ProactiveGateCompletion,
    ProactiveGateContext,
    ProactiveMode,
)
from agent.plugin_host import HostServices, PluginKernel
from bus.event_bus import EventBus
from bus.events_lifecycle import SceneObservationCommitted

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _context() -> ProactiveGateContext:
    return ProactiveGateContext(
        tick_id="tick",
        session_key="role:mira",
        now_utc=datetime.now(timezone.utc),
        target_transports=(("desktop", "role:mira"),),
    )


def _load_relationship_proactive_kernel(
    tmp_path: Path, *, relationship_runtime: object
) -> tuple[PluginKernel, EventBus]:
    root = tmp_path / "plugins"
    root.mkdir()
    shutil.copytree(
        _REPO_ROOT / "plugins" / "relationship_proactive",
        root / "relationship_proactive",
    )
    bus = EventBus()
    kernel = PluginKernel(
        [root],
        services=HostServices(event_bus=bus, relationship_runtime=relationship_runtime),
    )
    return kernel, bus


@pytest.mark.asyncio
async def test_scene_gate_claims_tick_and_advances_only_after_delivery(tmp_path: Path):
    runtime = MagicMock()
    runtime.should_trigger_scene_followup.return_value = (
        True,
        {"attempt_index": 1},
    )
    kernel, _bus = _load_relationship_proactive_kernel(tmp_path, relationship_runtime=runtime)
    await kernel.load_all()
    assert kernel.loaded_count == 1
    chain = ProactiveGateChain(kernel.proactive_gates)

    result = chain.evaluate(_context())

    assert result.activation is not None
    assert result.activation.mode == ProactiveMode.SCENE_FOLLOWUP
    runtime.should_trigger_proactive.assert_not_called()
    chain.finalize(
        ProactiveGateCompletion(
            activation=result.activation,
            session_key="role:mira",
            occurred_at=datetime.now(timezone.utc),
            outcome="delivered",
        )
    )
    runtime.handle_scene_followup_sent.assert_called_once()
    runtime.close_scene_followup.assert_not_called()


@pytest.mark.asyncio
async def test_loneliness_gate_blocks_when_relationship_runtime_rejects(tmp_path: Path):
    runtime = MagicMock()
    runtime.should_trigger_scene_followup.return_value = (False, {})
    runtime.should_trigger_proactive.return_value = (
        False,
        {
            "reason": "cooldown",
            "loneliness_value": 100,
            "trigger_threshold": 60,
        },
    )
    kernel, _bus = _load_relationship_proactive_kernel(tmp_path, relationship_runtime=runtime)
    await kernel.load_all()

    result = ProactiveGateChain(kernel.proactive_gates).evaluate(_context())

    assert result.blocked is True
    assert result.reason == "cooldown"
    assert result.blocked_gate_name == "relationship.loneliness"
    assert result.trace[1].metadata == {
        "reason": "cooldown",
        "loneliness_value": 100,
        "trigger_threshold": 60,
    }


@pytest.mark.asyncio
async def test_plugin_applies_shared_scene_observation(tmp_path: Path):
    runtime = MagicMock()
    kernel, bus = _load_relationship_proactive_kernel(tmp_path, relationship_runtime=runtime)
    await kernel.load_all()

    await bus.fanout(
        SceneObservationCommitted(
            session_key="role:mira",
            channel="desktop",
            chat_id="role:mira",
            role_id="mira",
            source="passive",
            transition="started",
            scene_key="rain",
            should_generate=True,
            prompt="1girl, rain",
        )
    )

    runtime.apply_scene_decision.assert_called_once_with(
        "role:mira",
        "started",
        "rain",
    )

    # 卸载后场景事件不应再触发 relationship_runtime，证明订阅挂在插件作用域上
    _ = await kernel.unload("relationship_proactive")
    await bus.fanout(
        SceneObservationCommitted(
            session_key="role:mira",
            channel="desktop",
            chat_id="role:mira",
            role_id="mira",
            source="passive",
            transition="closed",
            scene_key="",
            should_generate=False,
            prompt="",
        )
    )
    runtime.apply_scene_decision.assert_called_once()


@pytest.mark.asyncio
async def test_collects_and_clears_official_proactive_gates(tmp_path: Path):
    """setup() 必须与旧 proactive_gates() 等价：两个 gate 按声明顺序聚合进
    kernel.proactive_gates，卸载后整体清空——不只是"能驱动 gate 链"，而是
    "聚合面本身真的收纳了这两个 gate 且卸载会清掉"。"""
    runtime = MagicMock()
    kernel, _bus = _load_relationship_proactive_kernel(tmp_path, relationship_runtime=runtime)

    await kernel.load_all()

    assert [gate.name for gate in kernel.proactive_gates] == [
        "relationship.scene_followup",
        "relationship.loneliness",
    ]

    _ = await kernel.unload("relationship_proactive")
    assert kernel.proactive_gates == []


@pytest.mark.asyncio
async def test_setup_contributes_nothing_when_relationship_runtime_absent(tmp_path: Path):
    """relationship_runtime 未接线时插件仍加载成功但不贡献任何 gate/订阅。"""
    kernel, _bus = _load_relationship_proactive_kernel(tmp_path, relationship_runtime=None)

    await kernel.load_all()

    assert kernel.loaded_count == 1
    assert kernel.proactive_gates == []
