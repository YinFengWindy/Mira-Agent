"""Requests across the real plugin UI host boundary."""


async def plugin_bridge_request(service, method: str, payload=None):
    """Sends a request through the same host boundary used by plugin UI."""
    return await service.handle(
        {"id": method, "method": method, "payload": payload or {}},
        emit_event=lambda event: None,
    )
