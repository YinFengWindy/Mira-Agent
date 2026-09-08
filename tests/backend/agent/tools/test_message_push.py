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


@pytest.mark.parametrize("sender_name", ["text", "stream_text"])
async def test_delivery_metadata_keeps_legacy_senders_compatible(sender_name):
    tool = MessagePushTool()
    sender = AsyncMock()
    tool.register_channel("telegram", **{sender_name: sender})

    result = await tool.execute(
        channel="telegram", chat_id="one", message="scheduled",
        push_delivery_key="occurrence", push_message_already_persisted=True,
    )

    sender.assert_awaited_once_with("one", "scheduled")
    assert "已发送" in result


async def test_metadata_sender_uses_push_identity_not_shared_turn_identity():
    tool = MessagePushTool()
    sender = AsyncMock()
    tool.register_channel("desktop", text_with_metadata=sender)

    await tool.execute(
        channel="desktop", chat_id="one", message="first", delivery_key="turn",
    )
    sender.assert_awaited_once_with("one", "first", {
        "delivery_key": "", "already_persisted": False,
    })
    sender.reset_mock()
    await tool.execute(
        channel="desktop", chat_id="one", message="second", delivery_key="turn",
        push_delivery_key="occurrence", push_message_already_persisted=True,
    )
    sender.assert_awaited_once_with("one", "second", {
        "delivery_key": "occurrence", "already_persisted": True,
    })
