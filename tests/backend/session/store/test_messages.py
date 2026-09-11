"""Atomic deletion contracts for session message persistence."""

from pathlib import Path

import pytest

from session.store import SessionStore


@pytest.mark.parametrize("invalid_id", ["missing", "other:0", "session:0"])
def test_delete_rejects_partial_foreign_or_duplicate_ids_without_cursor_change(
    tmp_path: Path, invalid_id: str
):
    store = SessionStore(tmp_path / "sessions.db")
    try:
        for key in ["session", "other"]:
            store.create_session(key=key, metadata={})
            store.insert_message(
                key, role="user", content="question", ts="2026-09-11", seq=0
            )
        before = store.get_session_meta("session")
        with pytest.raises(ValueError, match="撤销消息已发生变化"):
            store.delete_session_messages_and_update_cursor(
                "session", ids=["session:0", invalid_id], last_consolidated=42
            )
        assert store.get_message("session:0") is not None
        assert store.get_message("other:0") is not None
        assert store.get_session_meta("session") == before
    finally:
        store.close()


def test_delete_rolls_back_when_database_skips_one_selected_row(tmp_path: Path):
    store = SessionStore(tmp_path / "sessions.db")
    try:
        store.create_session(key="session", metadata={})
        for seq in range(2):
            store.insert_message(
                "session", role="user", content="question", ts="2026-09-11", seq=seq
            )
        store._conn.execute(
            "CREATE TRIGGER keep_message BEFORE DELETE ON messages WHEN old.id = 'session:1' BEGIN SELECT RAISE(IGNORE); END"
        )
        store._conn.commit()
        before = store.get_session_meta("session")

        with pytest.raises(ValueError, match="撤销消息未完整删除"):
            store.delete_session_messages_and_update_cursor(
                "session", ids=["session:0", "session:1"], last_consolidated=42
            )

        assert [
            message["id"] for message in store.fetch_session_messages("session")
        ] == ["session:0", "session:1"]
        assert store.get_session_meta("session") == before
    finally:
        store.close()
