import asyncio
from contextlib import suppress
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bus.events import InboundMessage, OutboundMessage, SpawnCompletionItem
from bus.queue import MessageBus
from bootstrap.runtime.generations import RuntimeCandidate


@pytest.mark.asyncio
async def test_subscription_is_idempotent_and_can_be_removed():
    bus = MessageBus()
    received = []

    async def receive(message):
        received.append(message.content)

    bus.subscribe_outbound("chat", receive)
    bus.subscribe_outbound("chat", receive)
    await bus._dispatch_message(OutboundMessage(channel="chat", chat_id="one", content="hello"))
    assert received == ["hello"]
    bus.unsubscribe_outbound("chat", receive)
    await bus._dispatch_message(OutboundMessage(channel="chat", chat_id="one", content="removed"))
    assert received == ["hello"]


@pytest.mark.asyncio
async def test_buffered_message_uses_replacement_transport_after_handover():
    bus = MessageBus()
    received = []
    delivered = asyncio.Event()

    async def old(message):
        received.append("old")

    async def new(message):
        received.append(message.content)
        delivered.set()

    bus.subscribe_outbound("chat", old)
    async with bus.transport_lock:
        dispatcher = asyncio.create_task(bus.dispatch_outbound())
        await bus.publish_outbound(OutboundMessage(channel="chat", chat_id="one", content="buffered"))
        await asyncio.sleep(0)
        assert received == []
        bus.unsubscribe_outbound("chat", old)
        bus.subscribe_outbound("chat", new)
    try:
        await asyncio.wait_for(delivered.wait(), 1)
        assert received == ["buffered"]
    finally:
        bus.stop()
        dispatcher.cancel()
        with suppress(asyncio.CancelledError):
            await dispatcher


@pytest.mark.asyncio
async def test_late_completion_after_intake_closes_releases_its_generation():
    bus = MessageBus()
    await bus.close_inbound()
    core = SimpleNamespace(stop=AsyncMock(), memory_runtime=SimpleNamespace(aclose=AsyncMock()))
    generation = RuntimeCandidate(1, core, SimpleNamespace())
    retained = generation.acquire()
    await generation.retire()
    await bus.publish_inbound(SpawnCompletionItem("desktop", "one", object(), runtime_lease=retained))
    assert generation.drained.is_set()
    assert bus.inbound_size == 0


@pytest.mark.asyncio
async def test_message_bus_retries_failed_outbound_dispatch():
    bus = MessageBus()
    await bus.publish_inbound(InboundMessage("telegram", "u", "1", "hello"))
    inbound = await bus.consume_inbound()
    assert inbound.session_key == "telegram:1"

    sent: list[str] = []
    attempts = {"count": 0}

    async def callback(msg: OutboundMessage) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("first")
        sent.append(msg.content)

    bus.subscribe_outbound("telegram", callback)
    task = asyncio.create_task(bus.dispatch_outbound())
    await bus.publish_outbound(OutboundMessage("telegram", "1", "payload"))
    for _ in range(300):
        if sent:
            break
        await asyncio.sleep(0.01)
    bus.stop()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert sent == ["payload"]
    assert bus.inbound_size == 0
    assert bus.outbound_size == 0
