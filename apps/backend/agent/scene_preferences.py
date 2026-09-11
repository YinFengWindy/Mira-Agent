"""Core scene observation switch and one-time legacy disable migration."""

from pathlib import Path
from typing import Any

from agent.legacy_feature_preferences import (
    load_boolean_preferences,
    migrate_boolean_preferences,
)
from bootstrap.paths import REPOSITORY_ROOT, resource_root


def load_scene_preferences(data: dict[str, Any]) -> bool:
    """Loads the core scene switch without modifying a candidate's persisted config."""
    return load_boolean_preferences(
        data,
        section="scene_observation",
        keys=("enabled",),
        legacy_id="scene_awareness",
    )["enabled"]


def migrate_scene_preferences(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Preserves a retired scene plugin's explicit disable as the new core switch."""
    return migrate_boolean_preferences(
        path,
        data,
        section="scene_observation",
        keys=("enabled",),
        legacy_id="scene_awareness",
        roots=(
            resource_root() / "plugins",
            REPOSITORY_ROOT / "apps" / "backend" / "plugins",
        ),
    )
