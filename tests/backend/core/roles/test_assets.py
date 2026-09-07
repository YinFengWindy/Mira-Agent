from __future__ import annotations

import pytest
from pathlib import Path
from core.roles import assets as assets_module

from core.roles.assets import RoleAssetStore


def test_failed_asset_copy_removes_its_partial_target(tmp_path, monkeypatch):
    roles_dir = tmp_path / "roles"
    store = RoleAssetStore(roles_dir, roles_dir / "assets")
    source = tmp_path / "source.png"
    source.write_bytes(b"image")

    def partial_copy(_source, target):
        Path(target).write_bytes(b"partial")
        raise PermissionError("copy unavailable")

    monkeypatch.setattr(assets_module.shutil, "copy2", partial_copy)
    with pytest.raises(PermissionError, match="copy unavailable"):
        store.import_asset("mira", source, prefix="avatar")
    assert list((roles_dir / "assets" / "mira").iterdir()) == []


def test_asset_store_rejects_paths_outside_role_assets(tmp_path) -> None:
    roles_dir = tmp_path / "roles"
    assets_dir = roles_dir / "assets"
    assets_dir.mkdir(parents=True)
    store = RoleAssetStore(roles_dir, assets_dir)

    with pytest.raises(ValueError, match="路径越界"):
        store.resolve_path("../../outside.png")


def test_asset_store_rejects_duplicate_category_names(tmp_path) -> None:
    store = RoleAssetStore(tmp_path / "roles", tmp_path / "roles" / "assets")

    with pytest.raises(ValueError, match="分类名称不能重复"):
        store.normalize_categories(
            [
                {"id": "one", "name": "CG"},
                {"id": "two", "name": "cg"},
            ]
        )
