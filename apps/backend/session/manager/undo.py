"""Atomic passive-turn undo owned by the session manager."""

from collections.abc import Callable
from datetime import datetime

from .manager import _ManagerCoreMixin
from .undo_result import UndoSessionResult
from .undo_selection import _compute_rollback_index, _find_last_passive_turn


class _UndoMixin(_ManagerCoreMixin):
    async def undo_last_turn(
        self,
        session_key: str,
        *,
        rollback_source_resolver: Callable[[list[str]], list[str]] | None = None,
    ) -> UndoSessionResult | None:
        """Delete the latest committed passive turn under the session write lock.

        The synchronous resolver previews memory rollback sources while the selected
        message IDs are stable. Its failure leaves the session untouched. Pending
        message objects stay attached to the cached session for queued appends.
        """
        async with self._lock(session_key):
            messages = self._store.fetch_session_messages(session_key)
            target = _find_last_passive_turn(messages)
            if target is None:
                return None
            indices, user_index, assistant_index = target
            deleted_ids = [str(messages[index]["id"]) for index in indices]
            sources = (
                rollback_source_resolver(list(deleted_ids))
                if rollback_source_resolver is not None
                else []
            )
            meta = self._store.get_session_meta(session_key)
            old_last = max(0, int(meta["last_consolidated"])) if meta else 0
            rollback_index = _compute_rollback_index(
                messages,
                delete_indices=indices,
                old_last_consolidated=old_last,
                rollback_source_ids=sources,
            )
            new_last = max(
                0,
                min(
                    rollback_index - sum(index < rollback_index for index in indices),
                    len(messages) - len(indices),
                ),
            )
            # Include deleted threads even when their last turn disappears.
            thread_ids = {
                str(messages[index].get("thread_id") or "") for index in indices
            }

            def refresh_projections() -> None:
                for thread_id in sorted(thread_ids - {""}):
                    thread = self.conversation_store.get_thread(thread_id)
                    if thread is not None:
                        self._conversation_projector.project_thread(thread)

            # The store validates all IDs before deleting any row or changing cursor.
            _ = self._store.delete_session_messages_and_update_cursor(
                session_key,
                ids=deleted_ids,
                last_consolidated=new_last,
                refresh_projections=refresh_projections,
            )
            session = self._cache.get(session_key)
            if session is not None:
                deleted_set = set(deleted_ids)
                session.messages[:] = [
                    message
                    for message in session.messages
                    if message.get("id") not in deleted_set
                ]
                session.last_consolidated = new_last
                session.updated_at = datetime.now()
            return UndoSessionResult(
                deleted_ids=deleted_ids,
                target_user_id=str(messages[user_index]["id"]),
                target_assistant_id=str(messages[assistant_index]["id"]),
                rollback_index=rollback_index,
                last_consolidated_before=old_last,
                last_consolidated_after=new_last,
            )
