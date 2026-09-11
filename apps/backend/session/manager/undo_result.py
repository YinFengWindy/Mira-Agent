"""Public value result for an atomic session undo."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UndoSessionResult:
    """Persisted message identities and consolidation cursor affected by undo."""

    deleted_ids: list[str]
    target_user_id: str
    target_assistant_id: str
    rollback_index: int
    last_consolidated_before: int
    last_consolidated_after: int
