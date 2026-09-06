"""CHARX (ZIP) adapter with bounded, read-only extraction."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from .json_adapter import adapt_json
from .models import RoleCardAsset, RoleCardImportPreview, RoleCardImportReport
from .safety import (
    MAX_ARCHIVE_BYTES,
    MAX_ARCHIVE_MEMBERS,
    MAX_MEMBER_BYTES,
    MAX_SOURCE_BYTES,
    safe_archive_path,
    validate_image,
)


def adapt_charx(source: str | Path) -> RoleCardImportPreview:
    """Parse a CHARX card and return an in-memory preview without extraction."""
    path = Path(source).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"角色卡包不存在: {path}")
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("角色卡包超过大小限制")
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise ValueError("角色卡包不是有效 ZIP") from error
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_MEMBERS:
            raise ValueError("角色卡包文件数量超过限制")
        names: dict[str, zipfile.ZipInfo] = {}
        total_size = 0
        for info in infos:
            name = safe_archive_path(info.filename)
            if name in names:
                raise ValueError("角色卡包包含重复路径")
            if info.flag_bits & 0x1:
                raise ValueError("不支持加密角色卡包")
            if ((info.external_attr >> 16) & 0xF000) == 0xA000:
                raise ValueError("角色卡包不允许符号链接")
            if info.is_dir():
                continue
            if info.file_size > MAX_MEMBER_BYTES:
                raise ValueError("角色卡包文件超过大小限制")
            total_size += info.file_size
            if total_size > MAX_ARCHIVE_BYTES:
                raise ValueError("角色卡包解压总大小超过限制")
            names[name] = info
        if "card.json" not in names:
            raise ValueError("角色卡包根目录缺少 card.json")
        try:
            payload = json.loads(archive.read(names["card.json"]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, RuntimeError, zipfile.BadZipFile) as error:
            raise ValueError("角色卡包 card.json 无效") from error
        preview = adapt_json(payload, source_name="card.json", format_name="charx")
        assets: list[RoleCardAsset] = []
        unsupported_resources: list[str] = []
        for candidate in _referenced_assets(preview, payload, names):
            info = names.get(candidate.path)
            if info is None:
                unsupported_resources.append(candidate.path)
                continue
            try:
                raw = archive.read(info)
            except (RuntimeError, zipfile.BadZipFile) as error:
                raise ValueError(f"角色卡素材 {candidate.path} 无法读取") from error
            try:
                _, media_type = validate_image(raw, name=f"角色卡素材 {candidate.path}")
            except ValueError:
                unsupported_resources.append(candidate.path)
                continue
            assets.append(RoleCardAsset(kind=candidate.kind, name=candidate.name, path=candidate.path, data=raw, media_type=media_type))
        report = preview.report
        report = RoleCardImportReport(
            adapted_fields=report.adapted_fields,
            discarded_fields=report.discarded_fields,
            unsupported_macros=report.unsupported_macros,
            unsupported_resources=tuple(dict.fromkeys((*report.unsupported_resources, *unsupported_resources))),
            unsupported_rules=report.unsupported_rules,
        )
        return RoleCardImportPreview(
            name=preview.name,
            description=preview.description,
            profile=preview.profile,
            assets=tuple(assets),
            report=report,
            provenance=preview.provenance,
        )


def _referenced_assets(preview: RoleCardImportPreview, payload: Any, names: dict[str, zipfile.ZipInfo]) -> list[RoleCardAsset]:
    candidates = list(preview.assets)
    for name in names:
        if name == "card.json" or not _is_image_name(name):
            continue
        lower = name.casefold()
        if any(token in lower for token in ("user_icon", "user-icon", "model", "font", "audio", "video", "live2d", "3d")):
            continue
        if any(asset.path == name for asset in candidates):
            continue
        kind = "background" if "background" in lower else "emotion" if "emotion" in lower else "avatar" if "icon" in lower or "avatar" in lower or "main" in lower else "asset"
        emotion_name = Path(name).stem if kind == "emotion" else None
        candidates.append(RoleCardAsset(kind=kind, name=emotion_name, path=name))
    return candidates


def _is_image_name(value: str) -> bool:
    return Path(value).suffix.casefold() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
