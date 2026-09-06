"""Unified role-card preview service."""

from __future__ import annotations

import json
from pathlib import Path

from .charx_adapter import adapt_charx
from .json_adapter import adapt_json
from .models import RoleCardImportPreview
from .png_adapter import adapt_png
from .safety import MAX_SOURCE_BYTES


class RoleCardImportService:
    """Parse supported card formats without creating roles or copying assets."""

    def preview(self, source: str | Path) -> RoleCardImportPreview:
        path = Path(source).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"角色卡不存在: {path}")
        if path.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("角色卡超过大小限制")
        suffix = path.suffix.casefold()
        if suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("角色卡 JSON 无效") from error
            return adapt_json(payload, source_name=path.name)
        if suffix in {".png", ".apng"}:
            return adapt_png(path)
        if suffix == ".charx":
            return adapt_charx(path)
        raise ValueError("不支持的角色卡格式")

    def preview_bytes(self, data: bytes, *, filename: str) -> RoleCardImportPreview:
        """Write no files: parse bytes through the same bounded adapters."""
        if len(data) > MAX_SOURCE_BYTES:
            raise ValueError("角色卡超过大小限制")
        suffix = Path(filename).suffix.casefold()
        if suffix == ".json":
            try:
                payload = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("角色卡 JSON 无效") from error
            return adapt_json(payload, source_name=filename)
        raise ValueError("preview_bytes 仅支持 JSON；PNG/CHARX 请使用受控临时文件")
