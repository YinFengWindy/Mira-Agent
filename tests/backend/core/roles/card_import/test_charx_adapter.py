import io
import json
import zipfile

from PIL import Image

from core.roles.card_import.charx_adapter import adapt_charx_bytes


def test_archive_loads_only_declared_supported_images_and_reports_missing_or_invalid_bytes():
    image = io.BytesIO()
    Image.new("RGB", (8, 8)).save(image, format="PNG")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "card.json",
            json.dumps(
                {
                    "data": {
                        "name": "Test",
                        "assets": [
                            {
                                "type": "icon",
                                "name": "main",
                                "uri": "embeded://random.png",
                                "ext": "png",
                            },
                            {
                                "type": "emotion",
                                "name": "neutral",
                                "uri": "embeded://missing.png",
                                "ext": "png",
                            },
                            {
                                "type": "emotion",
                                "name": "sad",
                                "uri": "embeded://invalid.png",
                                "ext": "png",
                            },
                        ],
                    }
                }
            ),
        )
        archive.writestr("random.png", image.getvalue())
        archive.writestr("avatar/main.png", image.getvalue())
        archive.writestr("invalid.png", "not an image")
    preview = adapt_charx_bytes(buffer.getvalue())
    assert len(preview.assets) == 1
    assert preview.assets[0].kind == "avatar"
    assert preview.assets[0].path == "random.png"
    assert preview.assets[0].asset_id == "asset-0"
    assert set(preview.report.unsupported_resources) == {"missing.png", "invalid.png"}
