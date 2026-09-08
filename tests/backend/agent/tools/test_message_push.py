from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent.config_models import ChannelsConfig, Config, TelegramChannelConfig
from agent.tools.message_push import MessagePushTool
from core.common.runtime_scope import bind_runtime


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {},
    {"message": " \t\n"},
    {"file": "   "},
    {"image": "   "},
    {"message": " ", "file": "\t", "image": "\n"},
])
async def test_blank_payload_is_rejected_before_resolving_or_sending(payload):
    tool = MessagePushTool()
    send = AsyncMock()

    def resolve(_chat_id):
        raise AssertionError("empty payload must not resolve its target")

    tool.register_channel(
        "desktop", text=send, file=send, image=send, target_resolver=resolve,
    )

    result = await tool.execute(channel="desktop", chat_id="mira", **payload)

    assert result == "错误：message、file、image 至少提供一个"
    send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("message", "  hello\n"),
    ("file", "report with spaces.pdf"),
    ("image", "https://example.test/image.png"),
])
async def test_only_nonblank_fields_are_sent_without_changing_content(field, value):
    tool = MessagePushTool()
    senders = {name: AsyncMock() for name in ("message", "file", "image")}
    tool.register_channel(
        "desktop", text=senders["message"], file=senders["file"], image=senders["image"],
    )
    payload = dict.fromkeys(senders, " \t\n")
    payload[field] = value

    result = await tool.execute(channel="desktop", chat_id="mira", **payload)

    assert "已发送" in result
    for name, sender in senders.items():
        if name == field:
            sender.assert_awaited_once()
            assert sender.await_args.args[:2] == ("mira", value)
        else:
            sender.assert_not_awaited()


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
