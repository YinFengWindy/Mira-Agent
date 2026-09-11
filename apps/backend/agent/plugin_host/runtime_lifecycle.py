"""Runtime transitions that plugins can participate in without host special cases."""

from collections.abc import Awaitable, Callable


class PluginRuntimeLifecycle:
    """Exposes reload context and graceful draining of accepted background work."""

    def __init__(
        self,
        is_reload: bool,
        drainers: list[Callable[[], Awaitable[None]]],
        *,
        was_active: bool = False,
    ):
        self.is_reload = is_reload
        self.was_active = was_active
        self._drainers = drainers

    def on_drain(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Waits for accepted work before the old desktop transport is retired."""
        self._drainers.append(callback)
