from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from plugins.setup_helper.plugin import ChatIdCommandModule, setup


def _state(content: str, *, chat_id: str = "42", channel: str = "telegram") -> SimpleNamespace:
    return SimpleNamespace(
        session_key=f"{channel}:{chat_id}",
        msg=SimpleNamespace(
            content=content,
            channel=channel,
            chat_id=chat_id,
            timestamp=datetime.now(),
        ),
    )


@pytest.mark.asyncio
async def test_chatid_command_aborts_with_chat_id_reply() -> None:
    module = ChatIdCommandModule()
    frame = SimpleNamespace(input=_state("/chatid"), slots={})

    result = await module.run(frame)

    ctx = result.slots["session:ctx"]
    assert ctx.abort is True
    assert "42" in ctx.abort_reply
    assert 'channel = "telegram"' in ctx.abort_reply


@pytest.mark.asyncio
async def test_myid_alias_also_matches() -> None:
    module = ChatIdCommandModule()
    frame = SimpleNamespace(input=_state("/myid"), slots={})

    result = await module.run(frame)

    assert result.slots["session:ctx"].abort is True


@pytest.mark.asyncio
async def test_unrelated_command_is_ignored() -> None:
    module = ChatIdCommandModule()
    frame = SimpleNamespace(input=_state("/help"), slots={})

    result = await module.run(frame)

    assert "session:ctx" not in result.slots


@pytest.mark.asyncio
async def test_setup_contributes_before_turn_module_and_bot_command() -> None:
    """setup(ctx) 必须与旧 SetupHelper 的 before_turn_modules/telegram_bot_commands 等价。"""

    class _FakeLifecycle:
        def __init__(self) -> None:
            self.contributed: dict[str, list[object]] = {}

        def contribute(self, slot: str, modules: list[object]) -> None:
            self.contributed[slot] = modules

    class _FakeBotCommands:
        def __init__(self) -> None:
            self.added: list[tuple[str, str]] = []

        def add(self, command: str, description: str) -> None:
            self.added.append((command, description))

    class _FakeCtx:
        def __init__(self) -> None:
            self.lifecycle = _FakeLifecycle()
            self.bot_commands = _FakeBotCommands()

    ctx = _FakeCtx()
    await setup(ctx)

    assert [type(m).__name__ for m in ctx.lifecycle.contributed["before_turn"]] == [
        "ChatIdCommandModule"
    ]
    assert ctx.bot_commands.added == [("chatid", "查看我的 chat_id（配置 proactive 用）")]
