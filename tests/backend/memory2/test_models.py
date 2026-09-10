from __future__ import annotations

from memory2.models import MemoryItem


def test_memory_item_keeps_constructor_fields():
    item = MemoryItem(
        id="1",
        memory_type="procedure",
        summary="s",
        content_hash="h",
        embedding=[0.1],
        reinforcement=1,
        extra_json={},
        source_ref=None,
        happened_at=None,
        created_at="2025-01-01T00:00:00+00:00",
        updated_at="2025-01-01T00:00:00+00:00",
    )

    assert item.id == "1"
    assert item.memory_type == "procedure"
    assert item.embedding == [0.1]
