"""Normalize declared card assets without accessing remote or local files."""

from __future__ import annotations

from typing import Any

from .models import RoleCardAsset
from .safety import safe_archive_path

_IMAGE_EXTENSIONS = {"png", "apng", "jpg", "jpeg", "webp", "gif", "unknown"}


def normalize_assets(data: dict[str, Any]) -> tuple[list[RoleCardAsset], list[str]]:
    """Read V3 declarations, or the explicit image fields used by older cards."""
    if "assets" in data:
        return _v3_assets(data["assets"])
    declarations: list[tuple[str, str | None, str]] = []
    for key, kind in (
        ("avatar", "avatar"),
        ("icon", "avatar"),
        ("background", "background"),
        ("background_image", "background"),
    ):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            declarations.append((kind, None, value.strip()))
    for key in ("emotion_images", "emotions"):
        value = data.get(key)
        if isinstance(value, dict):
            declarations.extend(
                ("emotion", str(name).strip(), path.strip())
                for name, path in value.items()
                if isinstance(path, str) and path.strip()
            )
        elif isinstance(value, list):
            declarations.extend(
                (
                    "emotion",
                    str(item.get("name", "")).strip() or None,
                    item["path"].strip(),
                )
                for item in value
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            )
    assets: list[RoleCardAsset] = []
    unsupported: list[str] = []
    for index, (kind, name, uri) in enumerate(declarations):
        if ":" in uri and not uri.startswith("embeded://"):
            unsupported.append(uri)
            continue
        path = safe_archive_path(uri.removeprefix("embeded://"))
        assets.append(
            RoleCardAsset(kind=kind, name=name, path=path, asset_id=f"legacy-{index}")
        )
    return assets, unsupported


def _v3_assets(raw: Any) -> tuple[list[RoleCardAsset], list[str]]:
    if not isinstance(raw, list):
        return [], ["assets"]
    assets: list[RoleCardAsset] = []
    unsupported: list[str] = []
    for index, item in enumerate(raw):
        label = f"assets[{index}]"
        if not isinstance(item, dict) or not all(
            isinstance(item.get(key), str) for key in ("type", "name", "uri", "ext")
        ):
            unsupported.append(label)
            continue
        kind, name, uri, extension = (
            item[key].strip() for key in ("type", "name", "uri", "ext")
        )
        if kind == "user_icon" or (
            uri != "ccdefault:" and extension not in _IMAGE_EXTENSIONS
        ):
            unsupported.append(uri or label)
            continue
        if uri == "ccdefault:" and kind == "icon":
            path = uri
        elif uri.startswith("embeded://"):
            path = safe_archive_path(uri.removeprefix("embeded://"))
        else:
            unsupported.append(uri or label)
            continue
        mapped_kind = (
            "avatar"
            if kind == "icon" and name == "main"
            else (
                "background"
                if kind == "background" and name == "main"
                else "emotion" if kind == "emotion" and name else "asset"
            )
        )
        assets.append(
            RoleCardAsset(
                kind=mapped_kind,
                name=name or None,
                path=path,
                asset_id=f"asset-{index}",
            )
        )
    return assets, unsupported
