import pytest

from core.roles.card_import.asset_adapter import normalize_assets


def test_v3_uses_declared_types_names_and_uri_instead_of_filenames():
    assets, unsupported = normalize_assets(
        {
            "assets": [
                {
                    "type": "icon",
                    "name": "main",
                    "uri": "embeded://random/a.png",
                    "ext": "png",
                },
                {
                    "type": "background",
                    "name": "main",
                    "uri": "embeded://random/b.png",
                    "ext": "png",
                },
                {
                    "type": "emotion",
                    "name": "neutral",
                    "uri": "embeded://random/c.png",
                    "ext": "png",
                },
                {
                    "type": "emotion",
                    "name": "neutral",
                    "uri": "embeded://random/d.png",
                    "ext": "png",
                },
                {
                    "type": "x_image",
                    "name": "cover",
                    "uri": "embeded://avatar/main.png",
                    "ext": "png",
                },
            ]
        }
    )
    assert [(asset.kind, asset.name) for asset in assets] == [
        ("avatar", "main"),
        ("background", "main"),
        ("emotion", "neutral"),
        ("emotion", "neutral"),
        ("asset", "cover"),
    ]
    assert [asset.asset_id for asset in assets] == [
        f"asset-{index}" for index in range(5)
    ]
    assert assets[0].path == "random/a.png"
    assert unsupported == []


def test_unsupported_remote_user_and_nonimage_assets_are_reported():
    assets, unsupported = normalize_assets(
        {
            "assets": [
                {
                    "type": "icon",
                    "name": "main",
                    "uri": "https://example.com/a.png",
                    "ext": "png",
                },
                {
                    "type": "user_icon",
                    "name": "main",
                    "uri": "embeded://b.png",
                    "ext": "png",
                },
                {
                    "type": "x_audio",
                    "name": "voice",
                    "uri": "embeded://c.mp3",
                    "ext": "mp3",
                },
                {
                    "type": "icon",
                    "name": "main",
                    "uri": "file:///etc/image.png",
                    "ext": "png",
                },
            ]
        }
    )
    assert assets == []
    assert len(unsupported) == 4


def test_embedded_traversal_is_rejected():
    with pytest.raises(ValueError, match="路径不安全"):
        normalize_assets(
            {
                "assets": [
                    {
                        "type": "icon",
                        "name": "main",
                        "uri": "embeded://../a.png",
                        "ext": "png",
                    }
                ]
            }
        )
