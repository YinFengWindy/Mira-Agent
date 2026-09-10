from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from proactive_v2.anyaction import AnyActionGate, QuotaStore


def _gate_config() -> SimpleNamespace:
    return SimpleNamespace(
        anyaction_reset_hour_local=8,
        anyaction_timezone="UTC",
        anyaction_daily_max_actions=1,
        anyaction_min_interval_seconds=300,
        anyaction_idle_scale_minutes=60.0,
        anyaction_probability_min=0.1,
        anyaction_probability_max=0.9,
    )


def test_quota_store_counts_recorded_actions_within_the_day(tmp_path: Path):
    quota = QuotaStore(tmp_path / "quota.json")
    now = datetime(2025, 6, 1, 12, tzinfo=timezone.utc)

    assert quota.snapshot(now_utc=now, reset_hour=8, timezone_name="UTC").used == 0

    quota.record_action(now_utc=now, reset_hour=8, timezone_name="UTC")

    assert quota.snapshot(now_utc=now, reset_hour=8, timezone_name="UTC").used == 1


def test_gate_refuses_when_daily_quota_is_exhausted(tmp_path: Path):
    quota = QuotaStore(tmp_path / "quota.json")
    now = datetime(2025, 6, 1, 12, tzinfo=timezone.utc)
    quota.record_action(now_utc=now, reset_hour=8, timezone_name="UTC")
    gate = AnyActionGate(
        cfg=_gate_config(),
        quota_store=quota,
        rng=cast(Any, SimpleNamespace(random=lambda: 0.0)),
    )

    act, meta = gate.should_act(now_utc=now, last_user_at=now - timedelta(hours=2))

    assert act is False
    assert meta["reason"] == "quota_exhausted"


def test_gate_refuses_within_min_interval_after_last_action(tmp_path: Path):
    quota = QuotaStore(tmp_path / "quota.json")
    now = datetime(2025, 6, 1, 12, tzinfo=timezone.utc)
    quota.record_action(now_utc=now, reset_hour=8, timezone_name="UTC")
    cfg = _gate_config()
    cfg.anyaction_daily_max_actions = 3
    gate = AnyActionGate(
        cfg=cfg,
        quota_store=quota,
        rng=cast(Any, SimpleNamespace(random=lambda: 0.0)),
    )

    act, meta = gate.should_act(now_utc=now + timedelta(seconds=10), last_user_at=now)

    assert act is False
    assert meta["reason"] == "min_interval"


def test_gate_allows_action_when_quota_and_interval_permit(tmp_path: Path):
    cfg = _gate_config()
    cfg.anyaction_daily_max_actions = 3
    gate = AnyActionGate(
        cfg=cfg,
        quota_store=QuotaStore(tmp_path / "quota.json"),
        rng=cast(Any, SimpleNamespace(random=lambda: 0.0)),
    )
    now = datetime(2025, 6, 1, 12, tzinfo=timezone.utc)

    act, meta = gate.should_act(now_utc=now, last_user_at=now - timedelta(hours=2))

    assert act is True
    assert meta["reason"] == "probability"
