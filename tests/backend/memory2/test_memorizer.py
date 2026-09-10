from __future__ import annotations

from typing import Any, cast

import pytest

from memory2.memorizer import Memorizer
from memory2.store import MemoryStore2


@pytest.mark.asyncio
async def test_memorizer_profile_supersede_keeps_high_emotional_weight_item_under_092():
    class _Embedder:
        async def embed(self, text: str) -> list[float]:
            mapping = {
                "用户仍在等待 offer": [1.0, 0.0],
                "用户开始等待新的 offer": [0.91, 0.4146],
            }
            return mapping[text]

    store = MemoryStore2(":memory:")
    memorizer = Memorizer(store, cast(Any, _Embedder()))

    await memorizer.save_item(
        summary="用户仍在等待 offer",
        memory_type="profile",
        extra={"category": "status"},
        source_ref="old",
        emotional_weight=8,
    )
    await memorizer.save_item_with_supersede(
        summary="用户开始等待新的 offer",
        memory_type="profile",
        extra={"category": "status"},
        source_ref="new",
    )

    rows = store._db.execute(
        "SELECT source_ref, status FROM memory_items WHERE memory_type='profile' ORDER BY source_ref"
    ).fetchall()
    assert rows == [("new", "active"), ("old", "active")]


@pytest.mark.asyncio
async def test_memorizer_profile_supersede_retires_low_emotional_weight_item_at_091():
    class _Embedder:
        async def embed(self, text: str) -> list[float]:
            mapping = {
                "用户仍在等待 offer": [1.0, 0.0],
                "用户开始等待新的 offer": [0.91, 0.4146],
            }
            return mapping[text]

    store = MemoryStore2(":memory:")
    memorizer = Memorizer(store, cast(Any, _Embedder()))

    await memorizer.save_item(
        summary="用户仍在等待 offer",
        memory_type="profile",
        extra={"category": "status"},
        source_ref="old",
        emotional_weight=0,
    )
    await memorizer.save_item_with_supersede(
        summary="用户开始等待新的 offer",
        memory_type="profile",
        extra={"category": "status"},
        source_ref="new",
    )

    rows = store._db.execute(
        "SELECT source_ref, status FROM memory_items WHERE memory_type='profile' ORDER BY source_ref"
    ).fetchall()
    assert rows == [("new", "active"), ("old", "superseded")]
