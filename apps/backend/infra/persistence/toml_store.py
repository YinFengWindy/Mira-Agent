"""Structural TOML serialization with a lossless-value guard before persistence."""

from math import isnan
import tomllib
from typing import Any

import tomli_w


def render_toml(values: dict[str, Any]) -> str:
    """Serializes values, refusing any encoder change to their structure or types."""
    text = tomli_w.dumps(values)
    if not _equivalent(tomllib.loads(text), values):
        raise ValueError("TOML serialization changed configuration values")
    return text


def _equivalent(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _equivalent(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _equivalent(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, float) and isnan(left):
        return isnan(right)
    return left == right
