"""Scheduler-only fixtures and helpers for host tests."""

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from agent.scheduler import LatencyTracker, SchedulerService, ScheduledJob


def make_job(
    trigger="at",
    tier="instant",
    fire_at=None,
    channel="telegram",
    chat_id="123",
    message: str | None = "hello",
    prompt=None,
    name=None,
    interval_seconds=None,
    cron_expr=None,
    timezone_="UTC",
    role_id="mira",
) -> ScheduledJob:
    if fire_at is None:
        fire_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    return ScheduledJob(
        trigger=trigger,
        tier=tier,
        fire_at=fire_at,
        channel=channel,
        chat_id=chat_id,
        role_id=role_id,
        message=message,
        prompt=prompt,
        name=name,
        interval_seconds=interval_seconds,
        cron_expr=cron_expr,
        timezone=timezone_,
    )


@pytest.fixture
def mock_push():
    m = AsyncMock()
    m.execute = AsyncMock(return_value="文本已发送")
    return m


@pytest.fixture
def mock_loop():
    m = AsyncMock()
    m.process_direct = AsyncMock(return_value="AI response")

    async def _run_role_operation(_metadata, operation):
        return await operation()

    m.run_role_operation = AsyncMock(side_effect=_run_role_operation)
    return m


@pytest.fixture
def fixed_now():
    return datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def store_path(tmp_path) -> Path:
    return tmp_path / "schedules.json"


@pytest.fixture
def tracker():
    return LatencyTracker(default=25.0, window=20)


@pytest.fixture
def service(store_path, mock_push, mock_loop, fixed_now, tracker):
    return SchedulerService(
        store_path=store_path,
        push_tool=mock_push,
        agent_loop=mock_loop,
        tracker=tracker,
        _now_fn=lambda: fixed_now,
    )


async def drain_tasks():
    """Let all pending asyncio tasks finish."""
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        done, still_pending = await asyncio.wait(pending, timeout=1.0)
        if still_pending:
            for task in still_pending:
                task.cancel()
            await asyncio.gather(*still_pending, return_exceptions=True)
        if done:
            await asyncio.gather(*done, return_exceptions=True)
