"""Session-owned validation and persistence for prepared memory commits."""

import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from session.manager import ConsolidationCommitRequest, SessionManager


def _setup(tmp_path: Path):
    manager = SessionManager(tmp_path)
    session = manager.get_or_create("role:mira")
    session.add_message("user", "question")
    session.add_message("assistant", "answer")
    manager.save(session)
    request = ConsolidationCommitRequest(
        session_key=session.key,
        expected_message_ids=tuple(message["id"] for message in session.messages),
        expected_last_consolidated=0,
        last_consolidated=2,
    )
    return manager, session, request


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["cursor", "reordered", "missing_id"])
async def test_changed_cursor_or_source_ids_reject_before_memory_side_effects(
    tmp_path: Path, changed: str
):
    manager, session, request = _setup(tmp_path)
    if changed == "cursor":
        session.last_consolidated = 1
        manager.save(session)
    elif changed == "reordered":
        request = replace(
            request, expected_message_ids=tuple(reversed(request.expected_message_ids))
        )
    else:
        request = replace(
            request, expected_message_ids=(request.expected_message_ids[0], "")
        )
    write = AsyncMock()

    assert await manager.commit_consolidation(request, write) is False
    write.assert_not_awaited()
    assert session.last_consolidated == (1 if changed == "cursor" else 0)


@pytest.mark.asyncio
async def test_commit_allows_extended_persisted_prefix(tmp_path: Path):
    manager, session, request = _setup(tmp_path)
    session.add_message("user", "next question")
    session.add_message("assistant", "next answer")
    await manager.append_messages(session, session.messages[2:])
    write = AsyncMock()

    assert await manager.commit_consolidation(request, write) is True

    write.assert_awaited_once()
    assert len(session.messages) == 4
    assert session.last_consolidated == 2
    manager.invalidate(session.key)
    reloaded = manager.get_or_create(session.key)
    assert len(reloaded.messages) == 4
    assert reloaded.last_consolidated == 2


@pytest.mark.asyncio
async def test_commit_does_not_persist_pending_append_or_overwrite_its_messages(
    tmp_path: Path,
):
    manager, session, request = _setup(tmp_path)
    entered, resume = asyncio.Event(), asyncio.Event()

    async def write():
        entered.set()
        await resume.wait()

    task = asyncio.create_task(manager.commit_consolidation(request, write))
    await asyncio.wait_for(entered.wait(), timeout=2)
    session.add_message("user", "pending question")
    session.add_message("assistant", "pending answer")
    pending = session.messages[2:]
    resume.set()
    assert await asyncio.wait_for(task, timeout=2) is True
    assert all("id" not in message for message in pending)
    assert len(manager._store.fetch_session_messages(session.key)) == 2
    await manager.append_messages(session, pending)
    assert [message["id"] for message in session.messages] == [
        f"role:mira:{index}" for index in range(4)
    ]
    assert session.last_consolidated == 2


@pytest.mark.asyncio
async def test_failed_memory_write_preserves_persisted_and_cached_cursor(
    tmp_path: Path,
):
    manager, session, request = _setup(tmp_path)
    write = AsyncMock(side_effect=RuntimeError("memory write failed"))

    with pytest.raises(RuntimeError, match="memory write failed"):
        await manager.commit_consolidation(request, write)

    assert session.last_consolidated == 0
    manager.invalidate(session.key)
    assert manager.get_or_create(session.key).last_consolidated == 0


@pytest.mark.asyncio
async def test_failed_consumer_preserves_cursor_committed_after_memory_write(
    tmp_path: Path,
):
    manager, session, request = _setup(tmp_path)
    write = AsyncMock()
    publish = AsyncMock(side_effect=RuntimeError("memory consumer failed"))

    with pytest.raises(RuntimeError, match="memory consumer failed"):
        await manager.commit_consolidation(request, write, publish)

    write.assert_awaited_once()
    assert session.last_consolidated == 2
    manager.invalidate(session.key)
    assert manager.get_or_create(session.key).last_consolidated == 2
