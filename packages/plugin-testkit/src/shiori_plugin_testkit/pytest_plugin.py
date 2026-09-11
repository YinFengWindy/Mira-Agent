"""Real runtime fixture registered by the explicitly installed testkit distribution."""

import pytest
from shiori_plugin_testkit.packages import plugin_directory, stage_plugin_package


@pytest.fixture
def plugin_runtime(tmp_path, monkeypatch):
    """Starts an isolated reloadable host for a plugin package's integration tests."""
    from contextlib import asynccontextmanager

    from agent.config import load_config_text
    from bootstrap.app import AppRuntime, RuntimeFeatures
    from core.roles import RoleStore
    from desktop_bridge.runtime.service import ReloadableDesktopService

    @asynccontextmanager
    async def start(plugin_ids: tuple[str, ...], config_text: str = ""):
        plugin_root = tmp_path / "plugin_dirs"
        for plugin_id in plugin_ids:
            stage_plugin_package(
                plugin_directory(plugin_id),
                plugin_root / plugin_id,
            )
        monkeypatch.setattr(
            "bootstrap.tools._resolve_plugin_dirs", lambda workspace: [plugin_root]
        )
        text = (
            "[llm]\nregistrations = []\n"
            "\n[agent.maintenance]\nmemory_optimizer_enabled = false\n"
            '\n[proactive]\nenabled = false\nprofile = "quiet"\n' + config_text
        )
        path = tmp_path / "config.toml"
        path.write_text(text, encoding="utf-8")
        app = AppRuntime(
            load_config_text(text),
            tmp_path,
            features=RuntimeFeatures(
                enable_message_channels=False, enable_proactive=False
            ),
        )
        try:
            await app.start()
            service = ReloadableDesktopService(app, path, RoleStore(tmp_path))
            try:
                yield service, path
            finally:
                await service.aclose()
        finally:
            await app.shutdown()

    return start
