from __future__ import annotations

from agent.tools.shell import _MAX_OUTPUT, _truncate


def test_truncate_keeps_tail_and_drops_head_when_over_limit():
    truncated = _truncate("HEAD\n" + ("a" * 31000) + "\nTAIL")

    assert truncated["truncated"] is True
    assert truncated["strategy"] == "tail"
    assert "HEAD" not in truncated["text"]
    assert "TAIL" in truncated["text"]
    assert len(truncated["text"]) <= _MAX_OUTPUT
