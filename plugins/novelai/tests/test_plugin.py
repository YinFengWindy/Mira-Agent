from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from agent.lifecycle.types import AfterReasoningCtx, AfterToolResultCtx
from agent.plugin_host import HostServices, PluginKernel
from agent.tools.message_push import MessagePushTool
from agent.tools.registry import ToolRegistry
from bus.event_bus import EventBus
from bus.events_lifecycle import SceneObservationCommitted
from core.roles.store import RoleStore
from session.manager import SessionManager

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGIN_CONFIG = {"novelai": {"enabled": True, "token": "novel-token"}}


def _load_novelai_plugin(
    *,
    services: HostServices,
) -> PluginKernel:
    """Loads a fresh copy of the novelai plugin package through the real v2 kernel.

    Mirrors ``plugins/tool_loop_guard/tests/test_plugin.py``'s pattern: copying
    into a throwaway directory gives every test its own ``import_path`` so
    tests never collide through ``sys.modules`` caching. The copy only
    affects the *entry* module's own dynamic import; the plugin's internal
    ``plugins.novelai.backend.*`` sibling imports still resolve to the real,
    installed package either way.
    """
    with tempfile.TemporaryDirectory() as tmp:
        plugin_dir = Path(tmp) / "novelai"
        shutil.copytree(_REPO_ROOT / "plugins" / "novelai", plugin_dir)
        kernel = PluginKernel([Path(tmp)], services=services)
        asyncio.run(kernel.load_all())
        return kernel


def _services(
    tmp_path: Path,
    *,
    tool_registry: ToolRegistry | None = None,
    event_bus: EventBus | None = None,
    session_manager: object | None = None,
    plugin_configs: dict[str, dict[str, Any]] | None = None,
) -> HostServices:
    return HostServices(
        event_bus=event_bus or EventBus(),
        tool_registry=tool_registry or ToolRegistry(),
        workspace=tmp_path,
        session_manager=session_manager,
        plugin_configs=plugin_configs if plugin_configs is not None else _PLUGIN_CONFIG,
    )


@pytest.fixture(autouse=True)
def _fake_http_requester(monkeypatch: pytest.MonkeyPatch):
    """Stubs the shared HTTP requester factory before the plugin ever imports it.

    ``plugin.py`` does ``from core.net.http import get_default_http_requester``,
    a name binding resolved at import time. Patching
    ``core.net.http.get_default_http_requester`` here — before
    ``kernel.load_all()`` triggers that fresh import — is what actually takes
    effect; patching the plugin's own module object would not, because the
    kernel loads the entry file under a private, per-test import path (see
    ``_load_novelai_plugin``), never as ``plugins.novelai.backend.plugin``.
    """
    monkeypatch.setattr(
        "core.net.http.get_default_http_requester",
        lambda profile: SimpleNamespace(),
    )


def test_plugin_registers_tool_and_rpc_and_both_disappear_on_unload(
    tmp_path: Path,
) -> None:
    services = _services(tmp_path)
    kernel = _load_novelai_plugin(services=services)

    assert services.tool_registry is not None
    assert services.tool_registry.has_tool("generate_image") is True
    registered_rpc = (
        "plugin.novelai.generate",
        "plugin.novelai.regenerateMessageMedia",
        "plugin.novelai.history",
        "plugin.novelai.prompt_tags.list",
        "plugin.novelai.prompt_tags.upsert",
        "plugin.novelai.prompt_tags.delete",
    )
    for method in registered_rpc:
        assert kernel.rpc.resolve(method) is not None, method
    hook_names = [hook.name for hook in kernel.tool_hooks]
    assert "plugin:novelai:guard_auto_cg" in hook_names

    asyncio.run(kernel.unload("novelai"))

    assert services.tool_registry.has_tool("generate_image") is False
    for method in registered_rpc:
        assert kernel.rpc.resolve(method) is None, method
    assert kernel.tool_hooks == []


def test_plugin_attaches_media_produced_before_after_reasoning(tmp_path: Path) -> None:
    services = _services(tmp_path)
    _load_novelai_plugin(services=services)
    event_bus = services.event_bus

    async def _run() -> AfterReasoningCtx:
        await event_bus.emit(
            AfterToolResultCtx(
                session_key="role:mira",
                channel="desktop",
                chat_id="desktop",
                tool_name="generate_image",
                arguments={},
                result=json.dumps({"output_paths": [str(tmp_path / "output.png")]}),
                status="success",
            )
        )
        return await event_bus.emit(
            AfterReasoningCtx(
                session_key="role:mira",
                channel="desktop",
                chat_id="desktop",
                tools_used=(),
                thinking=None,
                response_metadata=cast(Any, SimpleNamespace(raw_text="ok")),
                streamed=False,
                tool_chain=(),
                context_retry={},
                reply="已生成",
            )
        )

    updated = asyncio.run(_run())

    assert updated.media == [str(tmp_path / "output.png")]


def test_plugin_does_not_attach_media_already_sent_by_message_push(
    tmp_path: Path,
) -> None:
    services = _services(tmp_path)
    _load_novelai_plugin(services=services)
    event_bus = services.event_bus
    image = str(tmp_path / "output.png")

    async def _run() -> AfterReasoningCtx:
        await event_bus.emit(
            AfterToolResultCtx(
                session_key="role:mira",
                channel="desktop",
                chat_id="desktop",
                tool_name="generate_image",
                arguments={},
                result=json.dumps({"output_paths": [image]}),
                status="success",
            )
        )
        await event_bus.emit(
            AfterToolResultCtx(
                session_key="role:mira",
                channel="desktop",
                chat_id="desktop",
                tool_name="message_push",
                arguments={"image": image},
                result="图片已发送",
                status="success",
            )
        )
        return await event_bus.emit(
            AfterReasoningCtx(
                session_key="role:mira",
                channel="desktop",
                chat_id="desktop",
                tools_used=(),
                thinking=None,
                response_metadata=cast(Any, SimpleNamespace(raw_text="ok")),
                streamed=False,
                tool_chain=(),
                context_retry={},
                reply="已发送",
            )
        )

    updated = asyncio.run(_run())

    assert updated.media == []


def test_plugin_wires_scene_observations_to_automatic_cg(tmp_path: Path) -> None:
    """Proves ``setup()`` actually connects the real event bus to AutoCgController.

    ``plugins/novelai/tests/test_auto_cg_controller.py`` already covers the
    controller's own scheduling/cooldown/retry behaviour directly (by calling
    ``.schedule()`` on a controller it constructs itself); what is new and
    decisive for the v2 migration is that ``ctx.events.on(SceneObservationCommitted,
    ...)`` in ``setup()`` actually reaches that controller through the plugin
    kernel's wiring, which this test alone exercises end to end.
    """
    _ = RoleStore(tmp_path).create_role(
        role_id="mira",
        name="Mira",
        system_prompt="粉色长发少女",
        runtime_config={"auto_scene_cg_enabled": True},
    )
    sessions = SessionManager(tmp_path)
    sessions.open_role_session("mira", role_name="Mira")
    event_bus = EventBus()
    registry = ToolRegistry()
    pushed = asyncio.Event()
    push_image = AsyncMock(side_effect=lambda *a, **kw: pushed.set())
    push_tool = MessagePushTool(event_bus=event_bus)
    push_tool.register_channel("telegram", image=push_image)
    registry.register(push_tool)
    services = _services(
        tmp_path,
        tool_registry=registry,
        event_bus=event_bus,
        session_manager=sessions,
    )
    _load_novelai_plugin(services=services)
    image_path = str(tmp_path / "cg.png")
    generate_tool = registry.get_tool("generate_image")
    assert generate_tool is not None
    generate = AsyncMock(return_value=json.dumps({"output_paths": [image_path]}))
    generate_tool.execute = generate

    async def _run() -> None:
        await event_bus.fanout(
            SceneObservationCommitted(
                session_key="role:mira",
                channel="telegram",
                chat_id="chat",
                role_id="mira",
                source="passive",
                transition="started",
                scene_key="rain-confession",
                visual_key="rain-confession-standing",
                should_generate=True,
                prompt="1girl, pink hair, standing in rain, emotional, night",
                negative_prompt="blurry, text",
                size_preset="portrait",
            )
        )
        await asyncio.wait_for(pushed.wait(), timeout=2)

    asyncio.run(_run())

    generated_arguments = generate.await_args.kwargs
    assert generated_arguments["scene_key"] == "rain-confession"
    assert generated_arguments["visual_key"] == "rain-confession-standing"
    assert "third-person view" in generated_arguments["prompt"]
    push_image.assert_awaited_once_with("chat", image_path)


class _BlockingImageTool:
    """Fakes the ``generate_image`` tool: blocks in ``execute`` until released.

    Parks a real in-flight ``AutoCgController`` task mid-generation so
    ``terminate()``'s ``await asyncio.gather(...)`` genuinely suspends,
    giving a concurrently fanned-out event a real window to land while
    unload is still in progress.
    """

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.call_count = 0

    async def execute(self, **_kwargs: object) -> str:
        self.call_count += 1
        self.entered.set()
        await self.release.wait()
        return json.dumps({"output_paths": ["cg.png"]})


def test_unload_unsubscribes_scene_observation_before_terminating_auto_cg(
    tmp_path: Path,
) -> None:
    """Regression for an unload-ordering defect caught in review: in
    ``setup()``, ``ctx.effect("auto_cg_controller", auto_cg_controller.terminate)``
    must be registered *before* ``ctx.events.on(SceneObservationCommitted,
    auto_cg_controller.schedule)`` — ``EffectScope.dispose_all`` pops LIFO
    (last registered, first disposed), so registering the effect first is
    what makes unload unsubscribe the event *before* awaiting
    ``terminate()``. Get the order backwards and ``terminate()`` runs while
    the subscription is still live.

    Modeled on ``plugins/scene_awareness/tests/test_plugin.py``'s
    ``test_unload_unsubscribes_proactive_handler_before_terminating_controller``,
    which caught the identical defect in that plugin (#183).

    ``AutoCgController.terminate()`` snapshots ``self._tasks``, cancels each,
    then awaits their completion. If ``SceneObservationCommitted`` is still
    subscribed during that await, a scene observation landing in the window
    calls ``schedule()`` and spawns a brand new task that is in neither the
    snapshot nor ever awaited — an orphaned generation call, leaked forever
    (``terminate()`` does not run a second time).

    Deterministic by construction: the fake tool blocks the first task at
    its one await point (``entered``/``release``), and a single
    ``asyncio.sleep(0)`` after starting ``kernel.unload()`` is enough to run
    its synchronous prefix — popping every effect down through
    ``auto_cg_controller.terminate``, whose own body up to the ``gather`` is
    synchronous too — without yet letting the cancelled first task's
    ``CancelledError`` actually land. Reverse-verified by hand (not part of
    this file): swapping the two registration lines back in ``plugin.py``
    makes this test fail on ``call_count == 1`` (it observes 2); restoring
    the fixed order makes it pass. Stable across 5 repeated runs in each
    direction.
    """
    _ = RoleStore(tmp_path).create_role(
        role_id="mira",
        name="Mira",
        system_prompt="粉发少女",
        runtime_config={"auto_scene_cg_enabled": True},
    )
    sessions = SessionManager(tmp_path)
    sessions.open_role_session("mira", role_name="Mira")
    registry = ToolRegistry()
    services = _services(tmp_path, tool_registry=registry, session_manager=sessions)
    kernel = _load_novelai_plugin(services=services)
    event_bus = services.event_bus
    fake_tool = _BlockingImageTool()
    generate_tool = registry.get_tool("generate_image")
    assert generate_tool is not None
    generate_tool.execute = fake_tool.execute

    def _observation(**overrides: object) -> SceneObservationCommitted:
        defaults: dict[str, object] = dict(
            session_key="role:mira",
            channel="desktop",
            chat_id="role:mira",
            role_id="mira",
            source="passive",
            transition="started",
            scene_key="rain-confession",
            visual_key="rain-confession-standing",
            should_generate=True,
            prompt="1girl, pink hair, standing in rain",
            negative_prompt="blurry",
            size_preset="portrait",
        )
        defaults.update(overrides)
        return SceneObservationCommitted(**defaults)

    async def _run() -> list[Exception]:
        # 1. Trigger the first scene observation and wait for its task to
        #    actually be parked inside execute() (it is already recorded in
        #    controller._tasks well before this, synchronously inside
        #    schedule()).
        await event_bus.fanout(_observation())
        await asyncio.wait_for(fake_tool.entered.wait(), timeout=2)
        fake_tool.entered.clear()

        # 2. Start unload concurrently; one sleep(0) runs it up to (but not
        #    past) terminate()'s gather suspend point.
        unload_task = asyncio.create_task(kernel.unload("novelai"))
        await asyncio.sleep(0)

        # 3. Fan out a second, independent scene observation while unload is
        #    suspended inside terminate()'s gather. Correct order: the
        #    subscription is already gone, so this is a no-op. Broken order:
        #    schedule() still fires and spawns an orphan task.
        await event_bus.fanout(
            _observation(session_key="role:mira-2", chat_id="role:mira-2")
        )

        fake_tool.release.set()
        errors = await asyncio.wait_for(unload_task, timeout=5)
        # Give any wrongly-spawned orphan task a chance to reach execute()
        # too before counting calls.
        await asyncio.sleep(0.05)
        return errors

    errors = asyncio.run(_run())

    assert errors == []
    assert fake_tool.call_count == 1
