"""Classifies SELF initialization independently of document existence."""

from __future__ import annotations

import hashlib

from core.memory.markdown_schema import DOCUMENT_DEFAULTS, render_memory_section

from .models import RoleRecord


def self_fingerprint(content: str) -> str:
    """Identifies document content while ignoring platform line endings."""
    return hashlib.sha256(
        content.replace("\r\n", "\n").strip().encode("utf-8")
    ).hexdigest()


def resolve_self_seed_state(role: RoleRecord, content: str):
    """Migrates legacy defaults and protects changes to a pending document."""
    state = dict(role.memory_init_state.get("self_seed") or {})
    fingerprint = self_fingerprint(content)
    if state:
        if state["status"] == "pending" and state["fingerprint"] != fingerprint:
            state["status"] = "user_edited"
        return state

    legacy = role.memory_init_state
    default = DOCUMENT_DEFAULTS["SELF.md"]
    local_default = default
    if legacy.get("seed_background_value"):
        local_default = render_memory_section(
            "SELF.md",
            local_default,
            "## 我的性格与形象",
            legacy["seed_background_value"],
        )
    source = str(legacy.get("relationship_baseline_source") or "")
    if source.startswith("seed") and legacy.get("relationship_baseline_value"):
        local_default = render_memory_section(
            "SELF.md",
            local_default,
            "## 我们的关系",
            f"来源: {source}\n\n{legacy['relationship_baseline_value']}",
        )
    known_default = not content.strip() or fingerprint in {
        self_fingerprint(default),
        self_fingerprint(local_default),
    }
    # Old generators also marked fallback templates ready; only known defaults retry.
    status = (
        "pending"
        if known_default
        else ("generated" if legacy.get("seed_self_ready") else "user_edited")
    )
    if source == "user_edited":
        status = "user_edited"
    return {"status": status, "fingerprint": fingerprint}
