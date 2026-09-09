"""作用域事件总线：拦截订阅并登记为 effect，修复插件直接 on() 后卸载不解绑的缺陷。"""

from __future__ import annotations

from typing import Any

from agent.plugin_host.effects import EffectScope
from bus.event_bus import EventBus


class ScopedEventBus:
    """插件视角的事件总线代理。

    on/off 被拦截并登记进 EffectScope，卸载插件时统一解绑；
    其余方法（emit/observe/fanout/enqueue 等）原样委托真实 EventBus。
    """

    def __init__(self, bus: EventBus, effects: EffectScope) -> None:
        self._bus = bus
        self._effects = effects

    def on(self, event_type: type, handler: Any) -> None:
        self._bus.on(event_type, handler)
        # EventBus.off 对已移除的 handler 幂等，插件在 terminate 里自行 off 也安全
        self._effects.add(
            f"event:{getattr(event_type, '__name__', event_type)}",
            lambda: self._bus.off(event_type, handler),
        )

    def off(self, event_type: type, handler: Any) -> None:
        self._bus.off(event_type, handler)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bus, name)
