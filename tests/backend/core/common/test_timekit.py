from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from core.common import timekit


def test_parse_iso_returns_aware_datetime_or_none():
    parsed = timekit.parse_iso("2025-06-01T09:00:00Z")

    assert parsed and parsed.tzinfo is not None
    assert timekit.parse_iso("bad") is None


def test_format_iso_emits_utc_offset():
    assert timekit.format_iso(datetime(2025, 1, 1)).endswith("+00:00")


def test_safe_zone_falls_back_to_utc_and_warns():
    logger = MagicMock()

    assert str(timekit.safe_zone("bad/zone", logger=logger)) == "UTC"
    logger.warning.assert_called_once()


def test_now_helpers_return_aware_datetimes():
    assert timekit.local_now("UTC").tzinfo is not None
    assert timekit.utcnow().tzinfo is not None
