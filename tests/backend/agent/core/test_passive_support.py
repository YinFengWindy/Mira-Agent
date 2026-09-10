from __future__ import annotations

from types import SimpleNamespace

from agent.core.passive_support import update_session_runtime_metadata


def _make_session() -> SimpleNamespace:
    session = SimpleNamespace()
    session.metadata = {}
    return session


def test_update_session_runtime_metadata_counts_tool_calls_across_groups():
    session = _make_session()
    tool_chain = [
        {"calls": [{"name": "shell"}, {"name": "web_search"}]},
        {"calls": [{"name": "read_file"}]},
    ]

    update_session_runtime_metadata(
        session,
        tools_used=["shell", "web_search", "read_file"],
        tool_chain=tool_chain,
    )

    assert session.metadata["last_turn_tool_calls_count"] == 3


def test_update_session_runtime_metadata_sets_iso_last_turn_ts():
    session = _make_session()

    update_session_runtime_metadata(session, tools_used=[], tool_chain=[])

    ts = session.metadata.get("last_turn_ts", "")
    assert ts and "T" in ts
