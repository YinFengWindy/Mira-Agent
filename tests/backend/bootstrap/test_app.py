from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.config_models import Config
from bootstrap.app import AppRuntime, DESKTOP_RUNTIME_FEATURES
from bootstrap.channels import start_channels


@pytest.fixture
def empty_config(monkeypatch):
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda _: [])
    return Config(provider="", model="", api_key="", model_registrations=[])


@pytest.mark.asyncio
async def test_app_runtime_start_passes_markdown_store_to_memory_optimizer(
    monkeypatch, tmp_path, empty_config,
):
    optimizer = MagicMock()
    build_optimizer = MagicMock(return_value=([], optimizer))
    monkeypatch.setattr("bootstrap.runtime_background.build_memory_optimizer_task", build_optimizer)
    app = AppRuntime(empty_config, tmp_path)

    try:
        await app.start()

        assert app.core is not None
        build_optimizer.assert_called_once()
        assert build_optimizer.call_args.args[0] is empty_config
        assert build_optimizer.call_args.kwargs["memory_store"] is app.core.memory_runtime.markdown.store
        assert build_optimizer.call_args.kwargs["role_runtime_registry"] is app.core.role_runtime_registry
        assert app._memory_optimizer is optimizer
    finally:
        await app.shutdown()


@pytest.mark.asyncio
async def test_app_runtime_desktop_mode_enables_message_channels(
    monkeypatch, tmp_path, empty_config,
):
    start_channel_host = AsyncMock(wraps=start_channels)
    monkeypatch.setattr("bootstrap.app.start_channels", start_channel_host)
    app = AppRuntime(empty_config, tmp_path, features=DESKTOP_RUNTIME_FEATURES)

    try:
        await app.start()

        start_channel_host.assert_awaited_once()
        assert start_channel_host.call_args.kwargs["enable_message_channels"] is True
        assert app.channel_host is not None
    finally:
        await app.shutdown()
