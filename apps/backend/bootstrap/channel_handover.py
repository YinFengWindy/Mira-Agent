"""Strict channel handover with explicit recovery status for configuration saves."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace

from bootstrap.channel_host import ChannelFailure, ChannelHandoverError, ChannelHost


def _failure(name: str, phase: str, error: BaseException):
    return ChannelFailure(name, phase, type(error).__name__, str(error))


async def handover_channels(
    active: ChannelHost, candidate: ChannelHost, *, commit: Callable[[], None] | None,
    retain_removed: bool = False,
):
    """Transfers connection ownership; callers must hold the transport barrier."""
    candidate_names = {channel.name for channel in candidate.channels}
    retired_replaced = [channel for name, channel in active._retired_transports.items() if name in candidate_names]
    removed = [channel for channel in active.channels if channel not in candidate.channels]
    removed.extend(retired_replaced)
    parked = [channel for channel in removed if retain_removed and channel.name not in candidate_names]
    for channel in parked:
        if not callable(getattr(channel, "pause_intake", None)) or not callable(getattr(channel, "resume_intake", None)):
            raise ValueError(f"Channel {channel.name} does not support draining removal")
    added = [channel for channel in candidate.channels if channel not in active.channels]
    stopped = []
    attempted = []
    current_name = "configuration"
    phase = "stop"
    try:
        for channel in reversed(removed):
            current_name = channel.name
            if channel in parked:
                channel.pause_intake()
                continue
            await channel.stop()
            stopped.append(channel)
        phase = "start"
        for channel in added:
            current_name = channel.name
            attempted.append(channel)
            await channel.start(replace(candidate._ctx_factory(channel), intake_paused=True))
        phase = "resume"
        for channel in candidate.channels:
            current_name = channel.name
            channel.resume_intake()
        # Intake callbacks cannot run on this loop between synchronous resume
        # and publication; any activation failure still precedes persistence.
        phase = "commit"
        current_name = "configuration"
        if commit is not None:
            commit()
    except BaseException as error:
        failure = _failure(current_name, phase, error)
        degraded = []
        # Cancel admission scheduled by a pre-commit resume before cleanup yields.
        for channel in attempted:
            try:
                channel.pause_intake()
            except BaseException as pause_error:
                degraded.append(_failure(channel.name, "candidate_pause", pause_error))
        # A failed stop has uncertain external state; do not create a duplicate connection.
        if phase == "stop":
            degraded.append(failure)
        for channel in reversed(attempted):
            try:
                await channel.stop()
            except BaseException as cleanup_error:
                degraded.append(_failure(channel.name, "candidate_cleanup", cleanup_error))
        unsafe_names = {item.channel for item in degraded}
        for channel in reversed(stopped):
            if channel.name in unsafe_names:
                continue
            try:
                await channel.start(active._ctx_factory(channel))
                if channel in retired_replaced:
                    channel.pause_intake()
                    active._ctx_factory(channel).push_tool.retire_channel(channel.name)
            except BaseException as restore_error:
                degraded.append(_failure(channel.name, "restore", restore_error))
        unsafe_names = {item.channel for item in degraded}
        for channel in active.channels:
            if channel.name in unsafe_names:
                continue
            try:
                channel.resume_intake()
            except BaseException as resume_error:
                degraded.append(_failure(channel.name, "resume", resume_error))
        active._failures.extend(degraded)
        if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
            raise
        if phase == "commit" and not degraded:
            raise
        raise ChannelHandoverError(failure, degraded) from error
    active._channels = candidate.channels
    active._configurations = dict(candidate._configurations)
    active._ctx_factory = candidate._ctx_factory
    active._failures = candidate.failures
    for channel in retired_replaced:
        active._retired_transports.pop(channel.name, None)
    return parked
