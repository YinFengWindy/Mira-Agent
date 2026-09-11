"""Session snapshot persistence regressions."""

from pathlib import Path

from session.manager import SessionManager


def test_session_clear_persists_deleted_messages(tmp_path: Path):
    manager = SessionManager(tmp_path)
    session = manager.get_or_create("cli:1")
    session.add_message("user", "question")
    session.add_message("assistant", "answer")
    manager.save(session)

    session.clear()
    manager.save(session)
    manager.invalidate(session.key)

    assert manager.get_or_create(session.key).messages == []
