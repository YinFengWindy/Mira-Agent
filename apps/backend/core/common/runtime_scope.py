"""Task-local ownership for work that must retain its starting configuration."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bootstrap.runtime.generations import RuntimeLease

_current: ContextVar[RuntimeLease | None] = ContextVar(
    "runtime_task_lease", default=None
)


def current_runtime_lease():
    """Returns the current task's lease without transferring ownership."""
    return _current.get()


@contextmanager
def bind_runtime(lease: RuntimeLease):
    """Makes a pinned generation available to child work through context propagation."""
    token = _current.set(lease)
    try:
        yield lease
    finally:
        _current.reset(token)
