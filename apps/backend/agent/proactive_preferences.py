"""Core proactive strategy switches and one-time legacy disable migration."""

from pathlib import Path
from typing import Any

from agent.legacy_feature_preferences import (
    load_boolean_preferences,
    migrate_boolean_preferences,
)
from bootstrap.paths import REPOSITORY_ROOT, resource_root
from proactive_v2.config import ProactiveStrategiesConfig

_STRATEGY_KEYS = ("scene_followup", "relationship")
_LEGACY_ID = "relationship_proactive"


def load_proactive_preferences(data: dict[str, Any]) -> ProactiveStrategiesConfig:
    """Loads independent strategy switches without modifying persisted candidate config."""
    return ProactiveStrategiesConfig(
        **load_boolean_preferences(
            data,
            section="proactive_strategies",
            keys=_STRATEGY_KEYS,
            legacy_id=_LEGACY_ID,
        )
    )


def migrate_proactive_preferences(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Preserves retired plugin preferences while existing core switches always win."""
    return migrate_boolean_preferences(
        path,
        data,
        section="proactive_strategies",
        keys=_STRATEGY_KEYS,
        legacy_id=_LEGACY_ID,
        roots=(
            resource_root() / "plugins",
            REPOSITORY_ROOT / "apps" / "backend" / "plugins",
        ),
    )
