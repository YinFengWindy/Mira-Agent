"""Data contracts for side-effect-free character-card imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..profile_models import ImportProvenance


@dataclass(frozen=True)
class RoleCardAsset:
    """A candidate asset discovered during preview, before role-owned copying."""

    kind: str
    path: str
    name: str | None = None
    data: bytes | None = field(default=None, repr=False, compare=False)
    media_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "path": self.path,
            "name": self.name,
            "media_type": self.media_type,
        }
        if self.data is not None:
            result["size"] = len(self.data)
        return result


@dataclass(frozen=True)
class RoleCardImportReport:
    """Compatibility diagnostics for one import operation."""

    adapted_fields: tuple[str, ...] = ()
    discarded_fields: tuple[str, ...] = ()
    unsupported_macros: tuple[str, ...] = ()
    unsupported_resources: tuple[str, ...] = ()
    unsupported_rules: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "adapted_fields": list(self.adapted_fields),
            "discarded_fields": list(self.discarded_fields),
            "unsupported_macros": list(self.unsupported_macros),
            "unsupported_resources": list(self.unsupported_resources),
            "unsupported_rules": list(self.unsupported_rules),
        }


@dataclass(frozen=True)
class RoleCardImportPreview:
    """Normalized card data returned by :class:`RoleCardImportService`."""

    name: str
    description: str
    profile: dict[str, Any]
    assets: tuple[RoleCardAsset, ...] = ()
    report: RoleCardImportReport = field(default_factory=RoleCardImportReport)
    provenance: ImportProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "profile": self.profile,
            "assets": [asset.to_dict() for asset in self.assets],
            "report": self.report.to_dict(),
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }
