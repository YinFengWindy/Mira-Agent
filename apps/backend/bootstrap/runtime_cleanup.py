"""Best-effort resource release with explicit error propagation at lifecycle boundaries."""

import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


async def run_cleanup_steps(*steps: tuple[str, Callable[[], Awaitable[None]]]) -> None:
    """Attempts every independent cleanup step and reports the first failure."""
    first_error: Exception | None = None
    for name, step in steps:
        try:
            await step()
        except Exception as exc:
            if first_error is None:
                first_error = exc
            logger.warning("shutdown step failed: %s: %s", name, exc)
    if first_error is not None:
        raise first_error
