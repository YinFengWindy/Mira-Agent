from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.lifecycle.types import AfterTurnCtx, BeforeTurnCtx
from agent.plugin_host import HostServices, PluginKernel, PluginState
from bus.event_bus import EventBus
from bus.events_lifecycle import ProactiveMessageCommitted
from core.roles.store import RoleStore
from session.manager import SessionManager

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_scene_awareness_kernel(
    tmp_path: Path,
    *,
    workspace: Path | None,
    session_manager: object = None,
    light_provider: object = None,
    light_model: str = "",
) -> tuple[PluginKernel, EventBus]:
    root = tmp_path / "plugins"
    root.mkdir()
    shutil.copytree(
        _REPO_ROOT / "plugins" / "scene_awareness", root / "scene_awareness"
    )
    bus = EventBus()
    kernel = PluginKernel(
        [root],
        services=HostServices(
            event_bus=bus,
            workspace=workspace,
            session_manager=session_manager,
            light_provider=light_provider,
            light_model=light_model,
        ),
    )
    return kernel, bus


def _before_turn_ctx(**overrides: object) -> BeforeTurnCtx:
    defaults: dict[str, object] = dict(
        session_key="cli:1",
        channel="cli",
        chat_id="1",
        content="hello",
        timestamp=datetime.now(timezone.utc),
        retrieved_memory_block="",
        retrieval_trace_raw=None,
        history_messages=(),
    )
    defaults.update(overrides)
    return BeforeTurnCtx(**defaults)


def _after_turn_ctx(**overrides: object) -> AfterTurnCtx:
    defaults: dict[str, object] = dict(
        session_key="cli:1",
        channel="cli",
        chat_id="1",
        reply="hi there",
        tools_used=(),
        thinking=None,
        will_dispatch=True,
    )
    defaults.update(overrides)
    return AfterTurnCtx(**defaults)


@pytest.mark.asyncio
async def test_setup_fails_without_workspace(tmp_path: Path) -> None:
    """workspace 缺失时插件加载失败并回滚，对齐旧 initialize() 的 raise。"""
    kernel, _bus = _load_scene_awareness_kernel(tmp_path, workspace=None)

    await kernel.load_all()

    assert kernel.loaded_count == 0
    states = {item["id"]: item for item in kernel.states()}
    assert states["scene_awareness"]["state"] == PluginState.FAILED.name
    assert "workspace" in states["scene_awareness"]["error"]


@pytest.mark.asyncio
async def test_setup_wires_before_after_turn_and_proactive_events(
    tmp_path: Path,
) -> None:
    """setup() 必须贡献与旧 SceneAwarenessPlugin 等价的三个事件订阅，且卸载后
    干净收尾（controller.terminate() 不抛异常，effect 真正撤销订阅）。"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    session_manager = SimpleNamespace(get_or_create=lambda key: SimpleNamespace(
        metadata={}, messages=()
    ))
    kernel, bus = _load_scene_awareness_kernel(
        tmp_path, workspace=workspace, session_manager=session_manager
    )

    await kernel.load_all()
    assert kernel.loaded_count == 1

    # before_turn 是 GATE：handler 必须把（未被改写的）ctx 原样传回
    before_ctx = _before_turn_ctx()
    result = await bus.emit(before_ctx)
    assert result is before_ctx

    # after_turn / proactive 只需确认订阅生效且不抛异常（controller 内部因缺少
    # light_provider 静默跳过调度，这部分业务逻辑由 test_controller.py 覆盖）
    _ = await bus.emit(_after_turn_ctx())
    await bus.fanout(
        ProactiveMessageCommitted(
            session_key="cli:1",
            channel="cli",
            chat_id="1",
            role_id="",
            assistant_response="hi",
            tools_used=(),
        )
    )

    errors = await kernel.unload("scene_awareness")
    assert errors == []

    # 卸载后事件订阅应已撤销：再次 emit 必须不再命中任何 handler，
    # bus.emit 在没有 handler 时原样返回同一个对象。
    after_before_ctx = _before_turn_ctx(session_key="cli:2")
    result_after_unload = await bus.emit(after_before_ctx)
    assert result_after_unload is after_before_ctx


class _BlockingLightProvider:
    """假 light_provider：chat() 挂起在 release 上，可控地制造一个仍在
    进行中的场景观察任务，供并发卸载测试制造竞争窗口。"""

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.chat_call_count = 0

    async def chat(self, **kwargs: object) -> SimpleNamespace:
        self.chat_call_count += 1
        self.entered.set()
        await self.release.wait()
        return SimpleNamespace(
            content="",
            tool_calls=[
                SimpleNamespace(
                    name="submit_scene_observation",
                    arguments={
                        "transition": "none",
                        "should_generate": False,
                        "scene_key": "",
                        "visual_key": "",
                        "prompt": "",
                        "negative_prompt": "",
                        "size_preset": "",
                    },
                )
            ],
        )


@pytest.mark.asyncio
async def test_unload_unsubscribes_proactive_handler_before_terminating_controller(
    tmp_path: Path,
) -> None:
    """回归 #183 复审发现的收尾顺序缺陷：``ctx.effect`` 必须先于三个
    ``ctx.events.on`` 登记，使 LIFO 卸载先撤销订阅、再 terminate controller。

    颠倒时会出现真实的任务泄漏：controller.terminate() 对 in-flight 任务做
    "snapshot -> cancel -> await gather -> clear()"；若在这个 await 窗口内
    ProactiveMessageCommitted 订阅仍然生效，一条新消息会通过
    schedule_proactive_turn 塞入一个不在 snapshot 里、因此不会被 cancel 的新
    任务，随后又被 clear() 丢弃引用——泄漏且永远不会完成。

    用真实并发验证：先让一个场景观察任务卡在 light_provider.chat() 里（确保
    controller.terminate() 的 gather 真的会挂起），卸载开始后、gather 仍在
    等待时再 fanout 第二条 ProactiveMessageCommitted。断言 chat() 只被调用
    过一次——如果收尾顺序颠倒，这条断言会失败（第二条消息会真的触发第二次
    chat() 调用，对应一个永远不会完成的孤儿任务）。
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    role_store = RoleStore(workspace)
    _ = role_store.create_role(
        role_id="mira",
        name="Mira",
        system_prompt="粉发少女",
        runtime_config={"auto_scene_cg_enabled": True},
    )
    sessions = SessionManager(workspace)
    sessions.open_role_session("mira", role_name="Mira")
    provider = _BlockingLightProvider()
    kernel, bus = _load_scene_awareness_kernel(
        tmp_path,
        workspace=workspace,
        session_manager=sessions,
        light_provider=provider,
        light_model="light-model",
    )
    await kernel.load_all()

    def _proactive_message(**overrides: object) -> ProactiveMessageCommitted:
        defaults: dict[str, object] = dict(
            session_key="role:mira",
            channel="desktop",
            chat_id="role:mira",
            role_id="mira",
            assistant_response="她忽然走近抱住了你。",
            tools_used=(),
        )
        defaults.update(overrides)
        return ProactiveMessageCommitted(**defaults)

    # 1. 触发第一个场景观察任务，等它真正卡进 chat() 的挂起点（此时它已经被
    #    收纳进 controller._tasks，之后 terminate() 的 snapshot 会包含它）。
    await bus.fanout(_proactive_message())
    await asyncio.wait_for(provider.entered.wait(), timeout=2)
    provider.entered.clear()

    # 2. 并发发起卸载。unload_task 创建后立即调度，其自身的第一段全同步执行
    #    （无论收尾顺序对错，都是：处置最先被 pop 到的 effect……直到轮到
    #    controller.terminate()，其内部 snapshot + cancel(task1) 均为同步代码，
    #    唯一的挂起点是随后的 gather）；单次 sleep(0) 足以让它跑到这个挂起点，
    #    且刚好还没来得及让 task1 的 CancelledError 真正投递（那需要额外的调度
    #    轮次）。多等一轮反而有把窗口错过的风险，因此这里刻意只 sleep(0) 一次。
    unload_task = asyncio.create_task(kernel.unload("scene_awareness"))
    await asyncio.sleep(0)

    # 3. 在这个挂起窗口内再 fanout 一条 ProactiveMessageCommitted。收尾顺序
    #    正确时，事件订阅已经撤销，这条消息不会被任何人处理。
    await bus.fanout(_proactive_message(session_key="role:mira-2", chat_id="role:mira-2"))

    provider.release.set()
    errors = await asyncio.wait_for(unload_task, timeout=5)
    assert errors == []

    # 给可能被错误创建的孤儿任务一点调度机会，让它也有机会调用 chat()。
    await asyncio.sleep(0.05)
    assert provider.chat_call_count == 1
