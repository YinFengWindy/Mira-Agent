import io

import pytest
from PIL import Image

from core.roles.card_import.models import RoleCardAsset
from desktop_bridge.role_card_import_assets import (
    resolve_emotion_selections,
    stage_assets,
    write_asset_preview,
)


def test_thumbnail_handles_undecodable_data_but_propagates_disk_failure(
    tmp_path, monkeypatch
):
    target = tmp_path / "preview.png"
    assert write_asset_preview(b"bad image", target) is False
    assert not target.exists()
    data = io.BytesIO()
    Image.new("RGB", (800, 800)).save(data, format="PNG")
    assert write_asset_preview(data.getvalue(), target)
    with Image.open(target) as image:
        assert image.size == (320, 320)

    def reject_save(*_args, **_kwargs):
        raise PermissionError("disk failure")

    monkeypatch.setattr(Image.Image, "save", reject_save)
    with pytest.raises(PermissionError, match="disk failure"):
        write_asset_preview(data.getvalue(), target)


def test_invalid_emotion_selections_are_rejected():
    assets = (
        RoleCardAsset(
            kind="emotion", name="neutral", path="a.png", asset_id="a", data=b"image"
        ),
    )
    assert resolve_emotion_selections(assets, None) == {"neutral": "a"}
    with pytest.raises(ValueError, match="选择无效"):
        resolve_emotion_selections(assets, {"unknown": "a"})


def test_staging_cleans_earlier_files_when_a_later_asset_is_invalid(tmp_path):
    assets = (
        RoleCardAsset(
            kind="asset", path="a.png", data=b"image", media_type="image/png"
        ),
        RoleCardAsset(kind="asset", path="b.png", data=b"invalid"),
    )
    with pytest.raises(ValueError, match="素材格式无效"):
        with stage_assets(assets, tmp_path):
            pytest.fail("invalid image format must fail before role creation")
    assert list(tmp_path.iterdir()) == []
