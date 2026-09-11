"""Package-local loaders and real host fixtures for status_commands tests."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.core.passive_turn import ContextStore
from agent.lifecycle.phases.before_turn import (
    BeforeTurnFrame,
    default_before_turn_modules,
)
from agent.lifecycle.types import TurnState
from agent.plugin_host import HostServices, PluginKernel
from bus.event_bus import EventBus
from bus.events import InboundMessage
from session.manager import Session

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def backend():
    name = "test_status_commands_backend"
    directory = PLUGIN_ROOT / "backend"
    spec = importlib.util.spec_from_file_location(
        name, directory / "plugin.py", submodule_search_locations=[str(directory)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    for key in list(sys.modules):
        if key == name or key.startswith(name + "."):
            del sys.modules[key]


@pytest.fixture
def kernel_factory(tmp_path: Path):
    @asynccontextmanager
    async def start(*, observe: str = "missing"):
        root = tmp_path / "plugins"
        shutil.copytree(PLUGIN_ROOT, root / "status_commands", ignore=shutil.ignore_patterns("__pycache__"))
        if observe != "missing":
            # The declared test dependency works both in a checkout and as an installed wheel.
            spec = importlib.util.find_spec("plugins.observe")
            assert spec is not None and spec.submodule_search_locations
            provider = Path(next(iter(spec.submodule_search_locations)))
            shutil.copytree(provider, root / "observe", ignore=shutil.ignore_patterns("__pycache__"))
            if observe in {"failed", "unexported"}:
                body = "raise RuntimeError('observe setup failed')" if observe == "failed" else "pass"
                _ = (root / "observe/backend/plugin.py").write_text(
                    f"async def setup(ctx):\n    {body}\n", encoding="utf-8",
                )
        bus = EventBus()
        kernel = PluginKernel(
            [root], namespace="status_integration",
            services=HostServices(
                event_bus=bus, workspace=tmp_path / "workspace",
                plugin_configs={"observe": {"enabled": observe != "disabled"}},
            ),
        )
        try:
            await kernel.load_all()
            yield kernel, bus
        finally:
            await kernel.terminate_all()

    return start


@pytest.fixture
def command_frame():
    def make(content: str, session: Session | None = None):
        session = session or Session(key="telegram:1")
        return BeforeTurnFrame(
            input=TurnState(
                msg=InboundMessage(channel="telegram", sender="user", chat_id="1", content=content),
                session_key=session.key, dispatch_outbound=True, session=session,
            ),
            slots={"session:session": session},
        )

    return make


@pytest.fixture
def run_command(command_frame):
    async def run(kernel: PluginKernel, bus: EventBus, content: str):
        frame = command_frame(content)
        session = frame.input.session
        manager = MagicMock(get_or_create=MagicMock(return_value=session))
        context_store = MagicMock(spec=ContextStore, prepare=AsyncMock())
        for module in default_before_turn_modules(
            bus, manager, context_store, plugin_modules=kernel.before_turn_modules,
        ):
            frame = await module.run(frame)
        assert frame.output is not None and frame.output.abort
        context_store.prepare.assert_not_awaited()
        assert frame.input.session is session
        assert session is not None and session.messages == []
        return frame.output.abort_reply

    return run
