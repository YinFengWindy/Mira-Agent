from __future__ import annotations

import sqlite3
from pathlib import Path

from memory2.store import MemoryStore2


def test_upsert_item_reinforces_equivalent_summaries(tmp_path: Path):
    store = MemoryStore2(tmp_path / "mem.db")
    try:
        first = store.upsert_item(
            "procedure", "Hello   world", [1.0, 0.0], source_ref="s1"
        )
        assert first.startswith("new:")
        item_id = first.split(":", 1)[1]

        assert store.upsert_item("procedure", "hello world", [1.0, 0.0]).startswith(
            "reinforced:"
        )
        # 标记 superseded 之后仍应命中同一条目并加固，而不是新建重复项
        store.mark_superseded(item_id)
        assert store.upsert_item("procedure", "hello world", [1.0, 0.0]).startswith(
            "reinforced:"
        )

        store.mark_superseded_batch([item_id])
        assert store.get_all_with_embedding(include_superseded=True)
        assert store.has_item_by_source_ref("s1", "procedure") is True
        assert store.delete_by_source_ref("s1") >= 1
    finally:
        store.close()


def test_upsert_consolidation_event_is_idempotent_per_source_ref(tmp_path: Path):
    store = MemoryStore2(tmp_path / "mem.db")
    try:
        created = store.upsert_consolidation_event(
            source_ref="r1", summary="Event A", embedding=[0.0, 1.0]
        )
        repeated = store.upsert_consolidation_event(
            source_ref="r1", summary="Event A", embedding=[0.0, 1.0]
        )

        assert created.startswith("new:")
        assert repeated.startswith("skipped:")
    finally:
        store.close()


def test_keyword_and_vector_search_filter_by_memory_type(tmp_path: Path):
    store = MemoryStore2(tmp_path / "mem.db")
    try:
        store.upsert_consolidation_event(
            source_ref="r1", summary="Event A", embedding=[0.0, 1.0]
        )
        store.upsert_item(
            "procedure",
            "Use pacman",
            [1.0, 0.0],
            extra={
                "trigger_tags": {
                    "scope": "tool_triggered",
                    "tools": [],
                    "skills": [],
                    "keywords": ["pacman"],
                }
            },
        )

        hits = store.keyword_match_procedures(["shell", "pacman"])
        results = store.vector_search([0.0, 1.0], top_k=2, memory_types=["event"])

        assert hits and hits[0]["memory_type"] == "procedure"
        assert results and results[0]["memory_type"] == "event"
        assert store.list_by_type("event")
    finally:
        store.close()


def test_record_replacements_keeps_both_summaries_and_extras(tmp_path: Path):
    store = MemoryStore2(tmp_path / "mem.db")
    try:
        old_res = store.upsert_item(
            "procedure",
            "旧流程：查 Steam 时直接用 web_search",
            [1.0, 0.0],
            source_ref="old-rule",
            extra={"tool_requirement": "web_search"},
        )
        new_res = store.upsert_item(
            "procedure",
            "新流程：查 Steam 时必须先用 steam_mcp",
            [0.9, 0.1],
            source_ref="new-rule",
            extra={"tool_requirement": "steam_mcp"},
        )
        old_item = store.get_items_by_ids([old_res.split(":", 1)[1]])[0]
        new_item = store.get_items_by_ids([new_res.split(":", 1)[1]])[0]

        recorded = store.record_replacements(
            old_items=[old_item],
            new_item=new_item,
            source_ref="test@replace",
        )

        assert recorded == 1
        replacements = store.list_replacements()
        assert replacements[0]["old_summary"] == "旧流程：查 Steam 时直接用 web_search"
        assert replacements[0]["new_summary"] == "新流程：查 Steam 时必须先用 steam_mcp"
        assert replacements[0]["old_extra_json"]["tool_requirement"] == "web_search"
        assert replacements[0]["new_extra_json"]["tool_requirement"] == "steam_mcp"
    finally:
        store.close()


def test_memory_store_runtime_migrates_emotional_weight_column(tmp_path: Path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE memory_items (
            id            TEXT PRIMARY KEY,
            memory_type   TEXT NOT NULL,
            summary       TEXT NOT NULL,
            content_hash  TEXT NOT NULL,
            embedding     TEXT,
            reinforcement INTEGER NOT NULL DEFAULT 1,
            extra_json    TEXT,
            source_ref    TEXT,
            happened_at   TEXT,
            status        TEXT NOT NULL DEFAULT 'active',
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL
        );
        """)
    conn.commit()
    conn.close()

    store = MemoryStore2(db_path)
    try:
        cols = {
            row[1]
            for row in store._db.execute("PRAGMA table_info(memory_items)").fetchall()
        }
        assert "emotional_weight" in cols
    finally:
        store.close()
