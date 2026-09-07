from __future__ import annotations

from .profile_models import RoleKnowledgeBase, RoleKnowledgeEntry


class RoleKnowledgeMatcher:
    """Select enabled Lorebook entries in deterministic priority and insertion order."""

    def match(
        self,
        knowledge_base: RoleKnowledgeBase,
        text: str = "",
    ) -> list[RoleKnowledgeEntry]:
        """Return every matching entry without truncating or budgeting its content."""
        if not knowledge_base.enabled:
            return []
        matched = [
            entry
            for entry in knowledge_base.entries
            if entry.enabled
            and entry.content.strip()
            and (entry.always_active or self._matches(entry, text))
        ]
        return sorted(
            matched, key=lambda entry: (-entry.priority, entry.insertion_order, entry.id)
        )

    @staticmethod
    def _matches(entry: RoleKnowledgeEntry, text: str) -> bool:
        primary = [key for key in entry.primary_keys if key.strip()]
        secondary = [key for key in entry.secondary_keys if key.strip()]
        # Secondary keys refine a primary match; they never trigger an entry alone.
        if not primary:
            return False
        haystack = text if entry.case_sensitive else text.casefold()

        def contains(key: str) -> bool:
            return (key if entry.case_sensitive else key.casefold()) in haystack

        return any(contains(key) for key in primary) and (
            not secondary or any(contains(key) for key in secondary)
        )
