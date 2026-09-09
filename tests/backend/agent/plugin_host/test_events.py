from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent.plugin_host.effects import EffectScope
from agent.plugin_host.events import ScopedEventBus
from bus.event_bus import EventBus


@dataclass
class _DemoEvent:
    value: str = ""


@pytest.mark.asyncio
async def test_scoped_on_is_unbound_by_dispose():
    bus = EventBus()
    scope = EffectScope("demo")
    scoped = ScopedEventBus(bus, scope)
    seen: list[str] = []

    async def handler(event: _DemoEvent) -> None:
        seen.append(event.value)

    scoped.on(_DemoEvent, handler)
    await bus.fanout(_DemoEvent(value="before"))
    assert seen == ["before"]

    await scope.dispose_all()
    await bus.fanout(_DemoEvent(value="after"))
    assert seen == ["before"]


@pytest.mark.asyncio
async def test_manual_off_then_dispose_is_safe():
    bus = EventBus()
    scope = EffectScope("demo")
    scoped = ScopedEventBus(bus, scope)

    async def handler(event: _DemoEvent) -> None:
        raise AssertionError("should not fire")

    scoped.on(_DemoEvent, handler)
    scoped.off(_DemoEvent, handler)
    await bus.fanout(_DemoEvent())
    # 插件自行 off 后，dispose 再次 off 不应报错
    assert await scope.dispose_all() == []


@pytest.mark.asyncio
async def test_non_subscription_methods_delegate_to_real_bus():
    bus = EventBus()
    scoped = ScopedEventBus(bus, EffectScope("demo"))
    seen: list[str] = []

    bus.on(_DemoEvent, lambda event: seen.append(event.value))
    # emit 等方法直接委托底层总线
    _ = await scoped.emit(_DemoEvent(value="delegated"))
    assert seen == ["delegated"]
