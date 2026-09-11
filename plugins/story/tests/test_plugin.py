"""Story's real assembly and required NovelAI lifecycle, without external requests."""

import asyncio
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.plugin_host import HostServices, PluginKernel
from agent.tools.registry import ToolRegistry
from bus.event_bus import EventBus


@pytest.mark.parametrize("novelai_enabled", [True, False])
def test_story_requires_active_novelai_and_unloads_before_it(
    tmp_path, monkeypatch, novelai_enabled
):
    root = Path(__file__).resolve().parents[3]
    packages = tmp_path / "packages"
    for name in ("novelai", "story"):
        shutil.copytree(
            root / "plugins" / name / "backend", packages / name / "backend"
        )
        shutil.copyfile(
            root / "plugins" / name / "manifest.yaml", packages / name / "manifest.yaml"
        )
    monkeypatch.setattr(
        "core.net.http.get_default_http_requester", lambda _: SimpleNamespace()
    )
    kernel = PluginKernel(
        [packages],
        services=HostServices(
            event_bus=EventBus(),
            tool_registry=ToolRegistry(),
            workspace=tmp_path / "workspace",
            plugin_configs={
                "novelai": {"enabled": novelai_enabled},
                "story": {"enabled": True},
            },
        ),
    )

    async def run():
        try:
            await kernel.load_all()
            states = {item["id"]: item for item in kernel.states()}
            if not novelai_enabled:
                assert states["story"]["state"] == "BLOCKED"
                assert "novelai" in states["story"]["error"]
                assert kernel.rpc.resolve("plugin.story.list") is None
                return
            assert states["story"]["state"] == "ACTIVE"
            resolved = kernel.rpc.resolve("plugin.story.list")
            assert resolved is not None
            assert await resolved[1]({}) == {"stories": []}
            assert kernel.rpc.resolve("plugin.story.cg.regenerate") is not None
            await kernel.unload("novelai")
            assert kernel.rpc.resolve("plugin.story.list") is None
            assert kernel.rpc.resolve("plugin.novelai.generate") is None
            assert (tmp_path / "workspace" / "stories").exists()
        finally:
            await kernel.terminate_all()

    asyncio.run(run())
