"""PNG/APNG Tavern metadata adapter."""

from __future__ import annotations

import base64
import binascii
import io
import json
import zlib
from pathlib import Path
from typing import Any

from PIL import Image

from .json_adapter import adapt_json
from .models import RoleCardAsset, RoleCardImportPreview
from .safety import validate_image


def adapt_png(source: str | Path) -> RoleCardImportPreview:
    """Read ``chara``/``ccv3`` metadata, preferring ccv3 when both exist."""
    path = Path(source).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"角色卡不存在: {path}")
    data = path.read_bytes()
    image_format, media_type = validate_image(data, name="角色卡图片")
    try:
        with Image.open(io.BytesIO(data)) as image:
            metadata = dict(image.info)
    except OSError as error:
        raise ValueError("角色卡图片无效") from error
    payload = None
    for key in ("ccv3", "chara"):
        if key in metadata:
            payload = _decode_metadata(metadata[key])
            if payload is not None:
                break
    if payload is None:
        raise ValueError("角色卡图片缺少 chara 或 ccv3 metadata")
    preview = adapt_json(payload, source_name=path.name, format_name="apng" if image_format == "PNG" and _is_animated(data) else "png")
    asset = RoleCardAsset(kind="avatar", path=path.name, data=data, media_type=media_type)
    return RoleCardImportPreview(
        name=preview.name,
        description=preview.description,
        profile=preview.profile,
        assets=(asset, *preview.assets),
        report=preview.report,
        provenance=preview.provenance,
    )


def _decode_metadata(value: Any) -> dict[str, Any] | None:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        try:
            raw = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            raw = value.encode("utf-8")
    else:
        return None
    for candidate in (raw, _inflate(raw)):
        if candidate is None:
            continue
        try:
            parsed = json.loads(candidate.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _inflate(raw: bytes) -> bytes | None:
    try:
        return zlib.decompress(raw)
    except zlib.error:
        return None


def _is_animated(data: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(data)) as image:
            return bool(getattr(image, "n_frames", 1) > 1)
    except OSError:
        return False

