import sys
from types import ModuleType
from unittest.mock import AsyncMock, Mock

import pytest

from agent.config_models import ChannelsConfig, Config, TelegramChannelConfig
from agent.tools.message_push import MessagePushTool
from bootstrap.channels import start_channels
from bus.event_bus import EventBus
from bus.queue import MessageBus
from core.net.http import SharedHttpResources
from session.manager import SessionManager
from plugins.qqbot.channel import QQBotChannel


@pytest.mark.asyncio
async def test_preparation_reuses_unchanged_connection_without_starting_traffic(tmp_path, monkeypatch):
    created = []

    class Telegram:
        def __init__(self, **kwargs):
            self.name = kwargs["channel_name"]
            self.start = AsyncMock()
            self.stop = AsyncMock()
            self.resume_intake = Mock()
            created.append(self)

    module = ModuleType("infra.channels.telegram_channel")
    module.TelegramChannel = Telegram
    monkeypatch.setitem(sys.modules, "infra.channels.telegram_channel", module)
    config = Config(provider="", model="", api_key="", channels=ChannelsConfig(telegram=TelegramChannelConfig(token="token")))
    resources = SharedHttpResources()
    context = dict(bus=MessageBus(), session_manager=SessionManager(tmp_path), push_tool=MessagePushTool(), http_resources=resources, event_bus=EventBus())
    try:
        active = await start_channels(config, **context)
        await active.start_all()
        candidate = await start_channels(config, previous_host=active, strict=True, **context)
        assert len(created) == 1
        assert candidate.channels == active.channels
        await active.handover(candidate)
        created[0].start.assert_awaited_once()
        created[0].stop.assert_not_awaited()
    finally:
        await resources.aclose()


@pytest.mark.asyncio
async def test_strict_preparation_surfaces_constructor_failure(tmp_path, monkeypatch):
    class Telegram:
        def __init__(self, **kwargs):
            raise ValueError("bad token format")

    module = ModuleType("infra.channels.telegram_channel")
    module.TelegramChannel = Telegram
    monkeypatch.setitem(sys.modules, "infra.channels.telegram_channel", module)
    config = Config(provider="", model="", api_key="", channels=ChannelsConfig(telegram=TelegramChannelConfig(token="bad")))
    resources = SharedHttpResources()
    try:
        with pytest.raises(ValueError, match="bad token format"):
            await start_channels(config, bus=MessageBus(), session_manager=SessionManager(tmp_path), push_tool=MessagePushTool(), http_resources=resources, event_bus=EventBus(), strict=True)
    finally:
        await resources.aclose()


@pytest.mark.asyncio
async def test_model_only_change_reuses_independently_owned_qqbot_connection(tmp_path):
    from dataclasses import replace

    config = Config(provider="", model="", api_key="")
    resources = SharedHttpResources()
    old = QQBotChannel("account-A", "secret-A")
    new = QQBotChannel("account-A", "secret-A")
    changed = QQBotChannel("account-B", "secret-B")
    context = dict(bus=MessageBus(), session_manager=SessionManager(tmp_path),
                   push_tool=MessagePushTool(), http_resources=resources, event_bus=EventBus())
    try:
        active = await start_channels(config, plugin_channels=[old], **context)
        candidate = await start_channels(replace(config, max_tokens=2048), plugin_channels=[new],
                                         previous_host=active, **context)
        assert candidate.channels == [old]
        assert not active.requires_exclusive_handover(candidate)
        assert new._client.is_closed
        replacement = await start_channels(config, plugin_channels=[changed], previous_host=active, **context)
        assert replacement.channels == [changed]
        assert active.requires_exclusive_handover(replacement)
    finally:
        await old.stop()
        await new.stop()
        await changed.stop()
        await resources.aclose()
