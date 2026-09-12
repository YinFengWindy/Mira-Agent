"""窄 handler：把 ``plugin.<id>.<method>`` 分发到插件经 RPC capability 注册的处理函数。

未注册方法与 ``plugin.config.*`` 一律返回 None，交由 ``DesktopBridgeService``
的兜底逻辑报 ``unknown_method``；``plugin.config.*`` 需要设置事务，由
``ReloadableDesktopService`` 的专用分支处理，见 desktop_bridge/runtime/service.py。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.plugin_host.rpc import PluginRpcRegistry


class DesktopPluginRequestHandler:
    """路由 ``plugin.<id>.<method>`` 到内核 RPC 注册表登记的处理函数。"""

    def __init__(self, registry: "PluginRpcRegistry | None") -> None:
        self._registry = registry

    async def handle(
        self, method: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Returns the plugin's result, or None when unresolved (falls through)."""
        if self._registry is None or not method.startswith("plugin."):
            return None
        if method.startswith("plugin.config."):
            return None
        resolved = self._registry.resolve(method)
        if resolved is None:
            return None
        _, handler = resolved
        result = await handler(payload)
        return result if result is not None else {}
