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
    monkeypatch,
    tmp_path,
    empty_config,
):
    optimizer = MagicMock()
    build_optimizer = MagicMock(return_value=([], optimizer))
    monkeypatch.setattr(
        "bootstrap.runtime.background.build_memory_optimizer_task", build_optimizer
    )
    app = AppRuntime(empty_config, tmp_path)

    try:
        await app.start()

        assert app.core is not None
        build_optimizer.assert_called_once()
        assert build_optimizer.call_args.args[0] is empty_config
        assert (
            build_optimizer.call_args.kwargs["memory_store"]
            is app.core.memory_runtime.markdown.store
        )
        assert (
            build_optimizer.call_args.kwargs["role_runtime_registry"]
            is app.core.role_runtime_registry
        )
        assert app._memory_optimizer is optimizer
    finally:
        await app.shutdown()


@pytest.mark.asyncio
async def test_app_runtime_desktop_mode_enables_message_channels(
    monkeypatch,
    tmp_path,
    empty_config,
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


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_initial_partial_core_failure_forces_unsafe_plugin_cleanup(
    tmp_path, monkeypatch, cancel
):
    import asyncio
    from pathlib import Path
    from shiori_plugin_testkit.packages import stage_plugin_package
    from bootstrap.tools import CoreRuntime

    packages = tmp_path / "plugins"
    stage_plugin_package(
        Path(__file__).resolve().parents[3] / "tests/fixtures/plugins/restart_required",
        packages / "restart_required",
    )
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda _: [packages])
    from agent.config_models import Config
    from bootstrap.app import AppRuntime, RuntimeFeatures

    config = Config(
        provider="",
        model="",
        api_key="",
        model_registrations=[],
        memory_optimizer_enabled=False,
    )
    app = AppRuntime(
        config,
        tmp_path,
        features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False),
    )
    states = []
    original_start = CoreRuntime.start

    async def partial_start(core):
        await original_start(core)
        states.append(core.plugin_manager._dependency_api("restart_required"))
        if cancel:
            raise asyncio.CancelledError()
        raise RuntimeError("initial start failed")

    monkeypatch.setattr(CoreRuntime, "start", partial_start)
    with pytest.raises(asyncio.CancelledError if cancel else RuntimeError):
        await app.start()
    assert states == [["started", "closed"]]
    assert app.core.plugin_manager.states() == []
    assert app.core.event_bus._closed
    assert app.http_resources._closed
