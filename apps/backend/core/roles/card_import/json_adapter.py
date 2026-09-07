"""Tavern V1/V2/V3 JSON adapter."""

from __future__ import annotations

import re
from typing import Any

from .lorebook_adapter import normalize_lorebook
from .models import ImportProvenance, RoleCardAsset, RoleCardImportPreview, RoleCardImportReport

_MACRO_PATTERN = re.compile(r"\{\{[^{}]+\}\}")


def adapt_json(payload: Any, *, source_name: str = "card.json", format_name: str = "tavern-json") -> RoleCardImportPreview:
    """Normalize a Tavern card object without reading or writing external state."""
    if not isinstance(payload, dict):
        raise ValueError("角色卡 JSON 必须是对象")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict):
        raise ValueError("角色卡 data 必须是对象")
    spec = str(payload.get("spec", "")).strip().lower()
    card_version = _version(payload, spec)
    name = _first_text(data, "name", "char_name") or "未命名角色"
    description = _first_text(data, "description")
    personality = _first_text(data, "personality")
    rules = _join_text(data.get("system_prompt"), data.get("post_history_instructions"))
    entries, lore_discarded = normalize_lorebook(data.get("character_book"))
    profile = {
        "version": 1,
        "character": {
            "profile": description,
            "personality": personality,
            "behavior_rules": rules,
        },
        "knowledge_base": {
            "enabled": bool(entries),
            "token_budget": 2000,
            "entries": entries,
        },
    }
    adapted = ["name", "description", "personality", "system_prompt"]
    if data.get("post_history_instructions"):
        adapted.append("post_history_instructions -> behavior_rules")
    if data.get("character_book"):
        adapted.append("character_book")
    discarded = list(lore_discarded)
    for field in ("first_mes", "first_message", "alternate_greetings"):
        if data.get(field):
            discarded.append(field)
    for field in ("scenario", "mes_example", "example_dialogue"):
        if data.get(field):
            discarded.append(field)
    macros = _macros(data)
    report = RoleCardImportReport(
        adapted_fields=tuple(dict.fromkeys(adapted)),
        discarded_fields=tuple(dict.fromkeys(discarded)),
        unsupported_macros=tuple(macros),
        unsupported_rules=tuple(_unsupported_rules(data)),
    )
    assets, unsupported_resources = _json_assets(data)
    report = RoleCardImportReport(
        adapted_fields=report.adapted_fields,
        discarded_fields=report.discarded_fields,
        unsupported_macros=report.unsupported_macros,
        unsupported_resources=tuple(dict.fromkeys((*report.unsupported_resources, *unsupported_resources))),
        unsupported_rules=report.unsupported_rules,
    )
    return RoleCardImportPreview(
        name=name,
        description=description,
        profile=profile,
        assets=tuple(assets),
        report=report,
        provenance=ImportProvenance(format=format_name, card_version=card_version),
    )


def _version(payload: dict[str, Any], spec: str) -> str | None:
    value = payload.get("spec_version") or payload.get("version")
    if value is None and "v3" in spec:
        return "V3"
    if value is None and "v2" in spec:
        return "V2"
    if value is None and spec:
        return "V1"
    if value is None:
        return None
    text = str(value).strip().upper()
    return text if text.startswith("V") else f"V{text.split('.', 1)[0]}"


def _first_text(data: dict[str, Any], *fields: str) -> str:
    for field in fields:
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _join_text(*values: Any) -> str:
    return "\n\n".join(value.strip() for value in values if isinstance(value, str) and value.strip())


def _macros(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.extend(_MACRO_PATTERN.findall(value))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_macros(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_macros(item))
    return list(dict.fromkeys(found))


def _unsupported_rules(data: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("extensions", "decorators", "recursive_scanning", "scan_depth", "insertion_order"):
        if data.get(key):
            values.append(key)
    return values


def _json_assets(data: dict[str, Any]) -> tuple[list[RoleCardAsset], list[str]]:
    assets: list[RoleCardAsset] = []
    unsupported: list[str] = []
    for key, kind in (("avatar", "avatar"), ("icon", "avatar"), ("background", "background"), ("background_image", "background")):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            if value.startswith(("http://", "https://")):
                unsupported.append(value.strip())
            else:
                assets.append(RoleCardAsset(kind=kind, path=value.strip()))
    for key in ("emotion_images", "emotions"):
        value = data.get(key)
        if isinstance(value, dict):
            for name, path in value.items():
                if isinstance(path, str) and path.strip():
                    assets.append(RoleCardAsset(kind="emotion", name=str(name), path=path.strip()))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("path"), str):
                    assets.append(RoleCardAsset(kind="emotion", name=str(item.get("name", "")) or None, path=item["path"].strip()))
    return assets, unsupported
