"""Semantic round trips for structured TOML persistence."""

import math
import tomllib
import pytest
from infra.persistence.toml_store import render_toml


def test_nested_types_and_quoted_names_survive_round_trip():
    values = {
        "plugins": {
            "unknown.id": {
                "enabled": False,
                "ports": [1, 2],
                "routes": [{"name": "日本語", "options": {"active": True}}],
            }
        }
    }
    assert tomllib.loads(render_toml(values)) == values


def test_nan_is_a_valid_toml_value():
    assert math.isnan(tomllib.loads(render_toml({"value": float("nan")}))["value"])


def test_unrepresentable_value_fails_instead_of_dropping_it():
    with pytest.raises(ValueError, match="changed configuration"):
        render_toml({"label": None})
