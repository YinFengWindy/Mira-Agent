"""Core proactive strategy configuration and one-time legacy disable migration."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import tomllib

from bootstrap.paths import REPOSITORY_ROOT, resource_root
from proactive_v2.config import ProactiveStrategiesConfig

_STRATEGY_KEYS = ("scene_followup", "relationship")
_LEGACY_ID = "relationship_proactive"


def load_proactive_preferences(data: dict[str, Any]) -> ProactiveStrategiesConfig:
    """Validates independent core switches, preserving old TOML candidates in memory."""
    raw = data.get("agent", {}).get("proactive_strategies", {})
    if not isinstance(raw, dict) or set(raw) - set(_STRATEGY_KEYS):
        raise ValueError(
            "agent.proactive_strategies only accepts scene_followup and relationship"
        )
    if any(not isinstance(value, bool) for value in raw.values()):
        raise ValueError("agent.proactive_strategies switches must be boolean")
    enabled = bool(data.get("plugins", {}).get(_LEGACY_ID, {}).get("enabled", True))
    return ProactiveStrategiesConfig(
        **{key: raw.get(key, enabled) for key in _STRATEGY_KEYS}
    )


def migrate_proactive_preferences(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Persists missing switches once; existing core choices always win over legacy state.

    Legacy markers may survive in read-only code locations. Once both core keys are
    present they are never consulted again; migration does not delete user files.
    Candidate validation uses load_proactive_preferences and never writes this file.
    """
    current = data.get("agent", {}).get("proactive_strategies", {})
    preferences = load_proactive_preferences(data)
    missing = [key for key in _STRATEGY_KEYS if key not in current]
    if not missing:
        return data
    roots = (
        resource_root() / "plugins",
        REPOSITORY_ROOT / "apps" / "backend" / "plugins",
    )
    disabled = any((root / _LEGACY_ID / "plugin.disabled").is_file() for root in roots)
    legacy = data.get("plugins", {}).get(_LEGACY_ID)
    if legacy is None and not disabled:
        return data
    values = {key: getattr(preferences, key) for key in _STRATEGY_KEYS}
    if disabled:
        for key in missing:
            values[key] = False
    from infra.persistence.text_store import atomic_save_text
    from desktop_bridge.plugin_config_text import merge_table

    text = path.read_text(encoding="utf-8")
    migrated = merge_table(text, ["agent", "proactive_strategies"], values)
    parsed = tomllib.loads(migrated)
    atomic_save_text(path, migrated)
    return parsed
