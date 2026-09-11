"""Owning locations for source checkout, installed wheels, and PyInstaller resources."""

from __future__ import annotations

from importlib.util import find_spec
import sys
from pathlib import Path

import shiori_runtime_resources

_candidate = Path(__file__).resolve().parents[3]
_SOURCE_ROOT = (
    _candidate
    if (_candidate / "apps/backend/bootstrap/paths.py").resolve()
    == Path(__file__).resolve()
    else None
)
# Compatibility for source-only migration probes. Installed resources never point outside the runtime distribution.
REPOSITORY_ROOT = (
    _SOURCE_ROOT or Path(shiori_runtime_resources.__file__).resolve().parent
)


def resource_root() -> Path:
    """Returns installed assets, the frozen bundle, or the canonical source resources."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if isinstance(frozen_root, str) and frozen_root:
        return Path(frozen_root)
    return REPOSITORY_ROOT


def plugin_roots() -> list[Path]:
    """Resolves actual plugin packages without bundling unrelated plugins into the host wheel."""
    if getattr(sys, "_MEIPASS", None) or _SOURCE_ROOT is not None:
        return [resource_root() / "plugins"]
    spec = find_spec("plugins")
    return (
        [Path(path) for path in spec.submodule_search_locations]
        if spec and spec.submodule_search_locations
        else []
    )


def builtin_skills_path() -> Path:
    """Locates production skills in all supported runtime distributions."""
    if _SOURCE_ROOT is not None and not getattr(sys, "_MEIPASS", None):
        return _SOURCE_ROOT / "apps/backend/skills"
    return resource_root() / "skills"


def common_emojis_path() -> Path:
    """Locates the canonical shared emoji asset shipped by both wheel and desktop bundle."""
    if _SOURCE_ROOT is not None and not getattr(sys, "_MEIPASS", None):
        return _SOURCE_ROOT / "apps/desktop/renderer/src/chat/common_emojis.json"
    return resource_root() / "common_emojis.json"


def common_emojis_paths(workspace: Path) -> list[Path]:
    """Preserves frozen-resource priority and development workspace overrides."""
    shared = common_emojis_path()
    override = workspace / "apps/desktop/renderer/src/chat/common_emojis.json"
    return [shared, override] if getattr(sys, "_MEIPASS", None) else [override, shared]


def ensure_repository_root_importable() -> None:
    """Adds only a real source checkout; installed packages use Python's normal import path."""
    if getattr(sys, "frozen", False) or _SOURCE_ROOT is None:
        return
    root = str(_SOURCE_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
