"""Validate and commit prepared memory consolidation under session ownership."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from .manager import _ManagerCoreMixin


@dataclass(frozen=True)
class ConsolidationCommitRequest:
    """Message prefix and cursor observed before preparing memory side effects."""

    session_key: str
    expected_message_ids: tuple[str, ...]
    expected_last_consolidated: int
    last_consolidated: int


class _ConsolidationMixin(_ManagerCoreMixin):
    async def commit_consolidation(
        self,
        request: ConsolidationCommitRequest,
        write_memory: Callable[[], Awaitable[None]],
        publish_committed: Callable[[], Awaitable[None]] | None = None,
    ) -> bool:
        """Commit a still-current draft and its cursor, serialized with undo.

        A changed prefix or cursor returns False before any memory side effect.
        New messages appended after the prepared prefix do not invalidate it.
        Write durable Markdown first, then persist the cursor and publish awaited
        memory consumers, all under one lock. A publishing failure preserves the
        already committed cursor and propagates to the caller. Neither callback
        may reacquire the session lock through save_async.
        Cancellation after commit starts is deferred until every started write and
        consumer settles, so a to_thread writer cannot outlive this lock.
        """
        if not 0 <= request.last_consolidated <= len(request.expected_message_ids):
            raise ValueError("整理游标超出准备的消息范围")
        async with self._lock(request.session_key):
            messages = self._store.fetch_session_messages(request.session_key)
            meta = self._store.get_session_meta(request.session_key)
            expected = request.expected_message_ids
            if (
                meta is None
                or not expected
                or not all(expected)
                or int(meta["last_consolidated"]) != request.expected_last_consolidated
                or tuple(str(message["id"]) for message in messages[: len(expected)])
                != expected
            ):
                return False

            async def finish_commit() -> None:
                await write_memory()
                self._store.update_last_consolidated(
                    request.session_key, request.last_consolidated
                )
                session = self._cache.get(request.session_key)
                if session is not None:
                    session.last_consolidated = request.last_consolidated
                    session.updated_at = datetime.now()
                if publish_committed is not None:
                    await publish_committed()

            # Cancelling an asyncio.to_thread await does not stop its underlying write.
            # Shield the whole commit and defer even repeated cancellation requests.
            pending = asyncio.gather(finish_commit(), return_exceptions=True)
            cancelled: asyncio.CancelledError | None = None
            while not pending.done():
                try:
                    await asyncio.shield(pending)
                except asyncio.CancelledError as exc:
                    cancelled = exc
            outcome = pending.result()[0]
            if cancelled is not None:
                if isinstance(outcome, BaseException):
                    raise cancelled from outcome
                raise cancelled
            if isinstance(outcome, BaseException):
                raise outcome
            return True
