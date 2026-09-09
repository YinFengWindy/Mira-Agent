from __future__ import annotations

from pathlib import Path

import pytest

from agent.plugin_host.manifest import (
    LEGACY_CAPABILITIES,
    ManifestError,
    load_manifest,
    synthesize_legacy_manifest,
)


def test_missing_manifest_returns_none(tmp_path: Path):
    assert load_manifest(tmp_path) is None


def test_legacy_four_field_manifest_keeps_api_one(tmp_path: Path):
    (tmp_path / "manifest.yaml").write_text(
        "name: qq_bot\nversion: '1.0'\ndesc: 渠道\nauthor: tester\n",
        encoding="utf-8",
    )
    manifest = load_manifest(tmp_path)
    assert manifest is not None
    assert not manifest.is_v2
    assert manifest.id == "qq_bot"
    # 旧 manifest 未声明 capabilities 时保持 legacy 全量能力
    assert manifest.capabilities == LEGACY_CAPABILITIES


def test_v2_manifest_parses_capabilities(tmp_path: Path):
    (tmp_path / "manifest.yaml").write_text(
        "api: 2\nid: demo\nversion: '0.1'\nentry: main.py\n"
        "capabilities:\n  - events\n  - kv\n",
        encoding="utf-8",
    )
    manifest = load_manifest(tmp_path)
    assert manifest is not None
    assert manifest.is_v2
    assert manifest.entry == "main.py"
    assert manifest.capabilities == ("events", "kv")


def test_v2_manifest_requires_capabilities(tmp_path: Path):
    (tmp_path / "manifest.yaml").write_text("api: 2\nid: demo\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="capabilities"):
        _ = load_manifest(tmp_path)


def test_unknown_capability_rejected(tmp_path: Path):
    (tmp_path / "manifest.yaml").write_text(
        "api: 2\nid: demo\ncapabilities:\n  - warp_drive\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="warp_drive"):
        _ = load_manifest(tmp_path)


def test_synthesized_legacy_manifest_grants_all(tmp_path: Path):
    manifest = synthesize_legacy_manifest(tmp_path / "hello")
    assert manifest.id == "hello"
    assert not manifest.is_v2
    assert manifest.capabilities == LEGACY_CAPABILITIES
