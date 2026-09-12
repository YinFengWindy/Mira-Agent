"""Process-wide ownership of exception hooks across overlapping plugin versions."""

from __future__ import annotations

import logging
import sys
import threading
from dataclasses import dataclass
from typing import Any


@dataclass
class _Hooks:
    owner: object
    handler: logging.Handler
    system: Any
    thread: Any
    loop: Any
    loop_handler: Any


_owners: list[_Hooks] = []
_original_system: Any = None
_original_thread: Any = None
_original_loop_handlers: dict[Any, Any] = {}


def install_global_hooks(owner, handler, system, thread, loop, loop_handler):
    """Installs one active collector, returning the original non-collector hooks."""
    global _original_system, _original_thread
    if not _owners:
        _original_system = sys.excepthook
        _original_thread = threading.excepthook
    else:
        logging.getLogger().removeHandler(_owners[-1].handler)
    if loop is not None and loop not in _original_loop_handlers:
        _original_loop_handlers[loop] = loop.get_exception_handler()
    hooks = _Hooks(owner, handler, system, thread, loop, loop_handler)
    _owners.append(hooks)
    logging.getLogger().addHandler(handler)
    sys.excepthook = system
    threading.excepthook = thread
    if loop is not None:
        loop.set_exception_handler(loop_handler)
    return _original_system, _original_thread, _original_loop_handlers.get(loop)


def uninstall_global_hooks(owner) -> None:
    """Removes any retired owner without restoring another retired collector."""
    index = next(
        (index for index, item in enumerate(_owners) if item.owner is owner), None
    )
    if index is None:
        return
    hooks = _owners.pop(index)
    logging.getLogger().removeHandler(hooks.handler)
    if index == len(_owners):
        previous = _owners[-1] if _owners else None
        if previous is not None:
            logging.getLogger().addHandler(previous.handler)
        if sys.excepthook == hooks.system:
            sys.excepthook = previous.system if previous else _original_system
        if threading.excepthook == hooks.thread:
            threading.excepthook = previous.thread if previous else _original_thread
        if hooks.loop is not None and not hooks.loop.is_closed():
            if hooks.loop.get_exception_handler() == hooks.loop_handler:
                hooks.loop.set_exception_handler(
                    previous.loop_handler
                    if previous and previous.loop is hooks.loop
                    else _original_loop_handlers.get(hooks.loop)
                )
    if not _owners:
        _original_loop_handlers.clear()
