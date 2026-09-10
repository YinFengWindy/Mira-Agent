from __future__ import annotations

from typing import Any, cast
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent.looping.ports import SessionServices
from agent.turns.orchestrator import TurnOrchestrator, TurnOrchestratorDeps
from agent.turns.outbound import OutboundDispatch, OutboundDispatchError
from agent.turns.result import TurnOutbound, TurnResult, TurnTrace
from bus.event_bus import EventBus
from bus.events_lifecycle import ProactiveMessageCommitted


class _DummySession:
    def __init__(self, key: str) -> None:
        self.key = key
        self.messages: list[dict[str, object]] = []
        self.metadata: dict[str, object] = {}
        self.last_consolidated = 0

    def add_message(self, role: str, content: str, media=None, **kwargs) -> None:
        msg: dict[str, object] = {
            "role": role,
            "content": content,
        }
        if media:
            msg["media"] = list(media)
        msg.update(kwargs)
        self.messages.append(msg)


@pytest.mark.asyncio
async def test_proactive_media_commit_notifies_shared_session() -> None:
    session = SimpleNamespace(
        key="role:mira",
        metadata={"role_id": "mira"},
        messages=[],
    )

    def add_message(role: str, content: str, media=None, **kwargs) -> None:
        session.messages.append(
            {
                "role": role,
                "content": content,
                "media": list(media or []),
                **kwargs,
            }
        )

    session.add_message = add_message
    session_manager = SimpleNamespace(
        get_or_create=lambda _key: session,
        append_messages=AsyncMock(return_value=None),
    )

    dispatched: list[OutboundDispatch] = []

    class _Outbound:
        result = True

        async def dispatch(self, outbound: OutboundDispatch) -> bool:
            dispatched.append(outbound)
            return self.result

    event_bus = EventBus()
    committed: list[ProactiveMessageCommitted] = []
    event_bus.on(ProactiveMessageCommitted, committed.append)
    outbound = _Outbound()
    orchestrator = TurnOrchestrator(
        TurnOrchestratorDeps(
            session=SessionServices(
                session_manager=cast(Any, session_manager),
                presence=None,
            ),
            outbound=outbound,
            event_bus=event_bus,
        )
    )

    result = TurnResult(
        decision="reply",
        outbound=TurnOutbound(
            session_key="role:mira",
            content="给你看张图",
            media=["D:\\media\\scene.png"],
        ),
    )
    await orchestrator.handle_proactive_turn(
        result=result,
        session_key="role:mira",
        channel="telegram",
        chat_id="123",
    )

    assert session.messages[0]["media"] == ["D:\\media\\scene.png"]
    assert dispatched[0].media == ["D:\\media\\scene.png"]
    assert committed == [
        ProactiveMessageCommitted(
            session_key="role:mira",
            channel="telegram",
            role_id="mira",
            chat_id="123",
            assistant_response="给你看张图",
            tools_used=("message_push",),
        )
    ]

    outbound.result = False
    committed.clear()
    sent = await orchestrator.handle_proactive_turn(
        result=result,
        session_key="role:mira",
        channel="telegram",
        chat_id="123",
    )

    assert sent is False
    assert committed == []


@pytest.mark.asyncio
async def test_proactive_retry_dispatches_without_recommitting_shared_session() -> None:
    session = SimpleNamespace(
        key="role:mira",
        metadata={"role_id": "mira"},
        messages=[],
    )
    session_manager = SimpleNamespace(
        get_or_create=lambda _key: session,
        append_messages=AsyncMock(return_value=None),
    )
    dispatched: list[OutboundDispatch] = []

    class _Outbound:
        async def dispatch(self, outbound: OutboundDispatch) -> bool:
            dispatched.append(outbound)
            return True

    event_bus = EventBus()
    committed: list[ProactiveMessageCommitted] = []
    event_bus.on(ProactiveMessageCommitted, committed.append)
    orchestrator = TurnOrchestrator(
        TurnOrchestratorDeps(
            session=SessionServices(
                session_manager=cast(Any, session_manager),
                presence=None,
            ),
            outbound=_Outbound(),
            event_bus=event_bus,
        )
    )
    result = TurnResult(
        decision="reply",
        outbound=TurnOutbound(
            session_key="role:mira",
            content="跨渠道提醒",
            media=["D:\\media\\scene.png"],
        ),
    )

    sent = await orchestrator.dispatch_proactive_retry(
        result=result,
        session_key="role:mira",
        channel="telegram",
        chat_id="123",
    )

    assert sent is True
    assert len(dispatched) == 1
    assert dispatched[0].channel == "telegram"
    assert dispatched[0].media == ["D:\\media\\scene.png"]
    session_manager.append_messages.assert_not_awaited()
    assert committed == []


@pytest.mark.asyncio
async def test_proactive_dispatch_error_is_not_converted_to_false() -> None:
    session = SimpleNamespace(
        key="role:mira",
        metadata={"role_id": "mira"},
        messages=[],
    )

    def add_message(role: str, content: str, media=None, **kwargs) -> None:
        session.messages.append({"role": role, "content": content, **kwargs})

    session.add_message = add_message
    session_manager = SimpleNamespace(
        get_or_create=lambda _key: session,
        append_messages=AsyncMock(return_value=None),
    )

    class _Outbound:
        async def dispatch(self, outbound: OutboundDispatch) -> bool:
            raise OutboundDispatchError(
                channel=outbound.channel,
                chat_id=outbound.chat_id,
                detail="network unavailable",
            )

    orchestrator = TurnOrchestrator(
        TurnOrchestratorDeps(
            session=SessionServices(
                session_manager=cast(Any, session_manager),
                presence=None,
            ),
            outbound=_Outbound(),
        )
    )
    failure_effect = SimpleNamespace(run=AsyncMock())

    with pytest.raises(OutboundDispatchError, match="network unavailable"):
        await orchestrator.handle_proactive_turn(
            result=TurnResult(
                decision="reply",
                outbound=TurnOutbound(session_key="role:mira", content="hello"),
                failure_side_effects=[failure_effect],
            ),
            session_key="role:mira",
            channel="telegram",
            chat_id="123",
        )

    failure_effect.run.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_orchestrator_skip_runs_side_effects_without_dispatch():
    order: list[str] = []

    class _Effect:
        async def run(self) -> None:
            order.append("side_effect")

    class _Outbound:
        async def dispatch(self, outbound: OutboundDispatch) -> bool:
            order.append("dispatch")
            return True

    orchestrator = TurnOrchestrator(
        TurnOrchestratorDeps(
            session=SessionServices(
                session_manager=cast(
                    Any,
                    SimpleNamespace(
                        get_or_create=lambda _key: _DummySession("telegram:123")
                    ),
                ),
                presence=None,
            ),
            outbound=_Outbound(),
        )
    )

    sent = await orchestrator.handle_proactive_turn(
        result=TurnResult(
            decision="skip",
            outbound=None,
            trace=TurnTrace(source="proactive", extra={"skip_reason": "quiet_hours"}),
            side_effects=[_Effect()],
        ),
        session_key="telegram:123",
        channel="telegram",
        chat_id="123",
    )

    assert sent is False
    assert order == ["side_effect"]


@pytest.mark.asyncio
async def test_orchestrator_proactive_reply_persists_dispatches_and_runs_success_effects():
    order: list[str] = []
    session = _DummySession("telegram:123")

    class _Effect:
        def __init__(self, name: str) -> None:
            self._name = name

        async def run(self) -> None:
            order.append(self._name)

    class _Outbound:
        async def dispatch(self, outbound: OutboundDispatch) -> bool:
            order.append("dispatch")
            assert outbound.content == "hello"
            return True

    presence = SimpleNamespace(
        record_proactive_sent=lambda _key: order.append("presence")
    )
    session_manager = SimpleNamespace(
        get_or_create=lambda _key: session,
        append_messages=AsyncMock(
            side_effect=lambda *_args, **_kwargs: order.append("persist")
        ),
    )
    orchestrator = TurnOrchestrator(
        TurnOrchestratorDeps(
            session=SessionServices(
                session_manager=cast(Any, session_manager),
                presence=cast(Any, presence),
            ),
            outbound=_Outbound(),
        )
    )

    sent = await orchestrator.handle_proactive_turn(
        result=TurnResult(
            decision="reply",
            outbound=TurnOutbound(session_key="telegram:123", content="hello"),
            evidence=["feed:1"],
            trace=TurnTrace(
                source="proactive",
                extra={
                    "tools_used": ["web_search"],
                    "tool_chain": [{"text": "", "calls": []}],
                    "steps_taken": 2,
                },
            ),
            side_effects=[_Effect("side_effect")],
            success_side_effects=[_Effect("success_effect")],
            failure_side_effects=[_Effect("failure_effect")],
        ),
        session_key="telegram:123",
        channel="telegram",
        chat_id="123",
    )

    assert sent is True
    assert session.messages[0]["proactive"] is True
    assert session.messages[0]["content"] == "hello"
    assert order == ["persist", "side_effect", "dispatch", "presence", "success_effect"]


@pytest.mark.asyncio
async def test_orchestrator_proactive_reply_records_presence_by_role_when_available():
    session = _DummySession("role:mira")
    session.metadata["role_id"] = "mira"
    calls: list[tuple[str, str]] = []

    class _Outbound:
        async def dispatch(self, outbound: OutboundDispatch) -> bool:
            return True

    presence = SimpleNamespace(
        record_proactive_sent=lambda _key: calls.append(("session", _key)),
        record_proactive_sent_by_role=lambda role_id: calls.append(("role", role_id)),
    )
    session_manager = SimpleNamespace(
        get_or_create=lambda _key: session,
        append_messages=AsyncMock(return_value=None),
    )
    orchestrator = TurnOrchestrator(
        TurnOrchestratorDeps(
            session=SessionServices(
                session_manager=cast(Any, session_manager),
                presence=cast(Any, presence),
            ),
            outbound=_Outbound(),
        )
    )

    sent = await orchestrator.handle_proactive_turn(
        result=TurnResult(
            decision="reply",
            outbound=TurnOutbound(session_key="role:mira", content="hello"),
        ),
        session_key="role:mira",
        channel="telegram",
        chat_id="123",
    )

    assert sent is True
    assert calls == [("role", "mira")]
