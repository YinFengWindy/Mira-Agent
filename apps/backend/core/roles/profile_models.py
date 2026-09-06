from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


@dataclass
class RoleKnowledgeEntry:
    """One normalized Lorebook entry used by the role prompt compiler."""

    content: str
    primary_keys: list[str] = field(default_factory=list)
    secondary_keys: list[str] = field(default_factory=list)
    enabled: bool = True
    always_active: bool = False
    case_sensitive: bool = False
    priority: int = 0
    insertion_order: int = 0
    id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "primary_keys": list(self.primary_keys),
            "secondary_keys": list(self.secondary_keys),
            "enabled": self.enabled,
            "always_active": self.always_active,
            "case_sensitive": self.case_sensitive,
            "priority": self.priority,
            "insertion_order": self.insertion_order,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RoleKnowledgeEntry":
        def words(name: str) -> list[str]:
            value = payload.get(name, [])
            if isinstance(value, str):
                value = [value]
            return [_text(item) for item in value if _text(item)] if isinstance(value, list) else []

        return cls(
            id=_text(payload.get("id")),
            content=_text(payload.get("content")),
            primary_keys=words("primary_keys"),
            secondary_keys=words("secondary_keys"),
            enabled=bool(payload.get("enabled", True)),
            always_active=bool(payload.get("always_active", False)),
            case_sensitive=bool(payload.get("case_sensitive", False)),
            priority=int(payload.get("priority") or 0),
            insertion_order=int(payload.get("insertion_order") or 0),
        )


@dataclass
class RoleKnowledgeBase:
    """Role-owned normalized Lorebook settings and entries."""

    enabled: bool = True
    token_budget: int = 2048
    entries: list[RoleKnowledgeEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "token_budget": max(0, int(self.token_budget)),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "RoleKnowledgeBase":
        data = payload if isinstance(payload, dict) else {}
        raw_entries = data.get("entries", [])
        entries = [
            RoleKnowledgeEntry.from_dict(item)
            for item in raw_entries
            if isinstance(item, dict)
        ]
        return cls(
            enabled=bool(data.get("enabled", True)),
            token_budget=max(0, int(data.get("token_budget") or 2048)),
            entries=entries,
        )


@dataclass
class RoleCharacterDefinition:
    """Stable role identity and behavior consumed by runtime prompts."""

    profile: str = ""
    personality: str = ""
    behavior_rules: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "profile": self.profile,
            "personality": self.personality,
            "behavior_rules": self.behavior_rules,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "RoleCharacterDefinition":
        data = payload if isinstance(payload, dict) else {}
        return cls(
            profile=_text(data.get("profile")),
            personality=_text(data.get("personality")),
            behavior_rules=_text(data.get("behavior_rules")),
        )


@dataclass
class RoleGreetings:
    """Default and alternate greetings stored without mutating session history."""

    default: str = ""
    alternates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"default": self.default, "alternates": list(self.alternates)}

    @classmethod
    def from_dict(cls, payload: Any) -> "RoleGreetings":
        data = payload if isinstance(payload, dict) else {}
        raw = data.get("alternates", [])
        return cls(
            default=_text(data.get("default")),
            alternates=[_text(item) for item in raw if _text(item)] if isinstance(raw, list) else [],
        )


@dataclass
class ImportProvenance:
    """Minimal optional source marker; it never participates in prompt rendering."""

    format: str
    card_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"format": self.format, "card_version": self.card_version}

    @classmethod
    def from_dict(cls, payload: Any) -> "ImportProvenance | None":
        if not isinstance(payload, dict):
            return None
        value = _text(payload.get("format"))
        return cls(value, _text(payload.get("card_version")) or None) if value else None


@dataclass
class RoleProfile:
    """Versioned Shiori runtime role definition."""

    version: int = 1
    character: RoleCharacterDefinition = field(default_factory=RoleCharacterDefinition)
    greetings: RoleGreetings = field(default_factory=RoleGreetings)
    knowledge_base: RoleKnowledgeBase = field(default_factory=RoleKnowledgeBase)
    import_provenance: ImportProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "version": int(self.version),
            "character": self.character.to_dict(),
            "greetings": self.greetings.to_dict(),
            "knowledge_base": self.knowledge_base.to_dict(),
        }
        if self.import_provenance is not None:
            payload["import_provenance"] = self.import_provenance.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Any) -> "RoleProfile":
        data = payload if isinstance(payload, dict) else {}
        return cls(
            version=max(1, int(data.get("version") or 1)),
            character=RoleCharacterDefinition.from_dict(data.get("character")),
            greetings=RoleGreetings.from_dict(data.get("greetings")),
            knowledge_base=RoleKnowledgeBase.from_dict(data.get("knowledge_base")),
            import_provenance=ImportProvenance.from_dict(data.get("import_provenance")),
        )

    @classmethod
    def from_legacy(cls, *, system_prompt: str, background: str) -> "RoleProfile":
        return cls(
            character=RoleCharacterDefinition(
                profile=_text(background),
                behavior_rules=_text(system_prompt),
            )
        )
