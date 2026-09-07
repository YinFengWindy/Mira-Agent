"""Normalization of Tavern character books into the Shiori knowledge shape."""

from __future__ import annotations

from typing import Any
from copy import deepcopy


def normalize_lorebook(raw: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Normalize supported character-book entries and report unsupported fields."""
    if raw is None:
        return [], []
    if not isinstance(raw, dict):
        return [], ["character_book"]
    raw_entries = raw.get("entries", [])
    if not isinstance(raw_entries, list):
        return [], ["character_book.entries"]
    entries: list[dict[str, Any]] = []
    discarded: list[str] = []
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, dict):
            discarded.append(f"character_book.entries[{index}]")
            continue
        keys = _string_list(raw_entry.get("keys"))
        secondary_keys = _string_list(
            raw_entry.get("secondary_keys", raw_entry.get("secondaryKeys"))
        )
        raw_title = raw_entry.get("title", "")
        title = raw_title.strip() if isinstance(raw_title, str) else ""
        content = raw_entry.get("content", "")
        if not isinstance(content, str) or not content.strip():
            discarded.append(f"character_book.entries[{index}].content")
            continue
        entry: dict[str, Any] = {
            "id": str(raw_entry.get("id", index)).strip() or str(index),
            "title": title,
            "content": content,
            "primary_keys": keys,
            "secondary_keys": secondary_keys,
            "enabled": bool(raw_entry.get("enabled", True)),
            "always_active": bool(
                raw_entry.get("constant", raw_entry.get("always", False))
            ),
            "case_sensitive": bool(
                raw_entry.get("case_sensitive", raw_entry.get("caseSensitive", False))
            ),
            "priority": _integer(raw_entry.get("priority"), 0),
            "insertion_order": _integer(
                raw_entry.get("insertion_order", raw_entry.get("order", index)), index
            ),
            "raw_source": deepcopy(raw_entry),
        }
        entries.append(entry)
        for unsupported in ("selectiveLogic", "scan_depth", "position", "extensions"):
            if unsupported in raw_entry:
                discarded.append(f"character_book.entries[{index}].{unsupported}")
    entries.sort(
        key=lambda item: (
            -int(item["priority"]),
            int(item["insertion_order"]),
            str(item["id"]),
        )
    )
    return entries, discarded


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _integer(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
