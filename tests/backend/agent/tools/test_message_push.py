from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent.config_models import ChannelsConfig, Config, TelegramChannelConfig
from agent.tools.message_push import MessagePushTool
from core.common.runtime_scope import bind_runtime


@pytest.mark.asyncio
async def test_retired_transport_only_sends_for_previously_accepted_generation():
    tool = MessagePushTool()
    send = AsyncMock()
    tool.register_channel("telegram", text=send)
    tool.retire_channel("telegram")
    old = SimpleNamespace(config=Config(provider="", model="", api_key="", channels=ChannelsConfig(telegram=TelegramChannelConfig(token="old"))))
    new = SimpleNamespace(config=Config(provider="", model="", api_key=""), core=SimpleNamespace(plugin_manager=None))

    with bind_runtime(old):
        await tool.execute(channel="telegram", chat_id="one", message="accepted")
    with bind_runtime(new):
        result = await tool.execute(channel="telegram", chat_id="one", message="new")
    send.assert_awaited_once_with("one", "accepted")
    assert "已停用" in result
