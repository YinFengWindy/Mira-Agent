from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bootstrap.paths import (
    REPOSITORY_ROOT,
    ensure_repository_root_importable,
    resource_root,
)


def test_repository_root_is_the_directory_holding_apps_and_plugins() -> None:
    assert (REPOSITORY_ROOT / "apps" / "backend").is_dir()
    assert (REPOSITORY_ROOT / "plugins").is_dir()


def test_resource_root_is_the_repository_root_in_dev() -> None:
    assert resource_root() == REPOSITORY_ROOT


def test_resource_root_follows_the_bundle_root_when_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert resource_root() == tmp_path


def test_ensure_repository_root_importable_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != str(REPOSITORY_ROOT)])

    ensure_repository_root_importable()
    ensure_repository_root_importable()

    assert sys.path.count(str(REPOSITORY_ROOT)) == 1


def test_ensure_repository_root_importable_leaves_frozen_runs_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """冻结态由 PyInstaller 直接收集 plugins.*，注入仓库根路径既无用也不正确。"""
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != str(REPOSITORY_ROOT)])
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    ensure_repository_root_importable()

    assert str(REPOSITORY_ROOT) not in sys.path
