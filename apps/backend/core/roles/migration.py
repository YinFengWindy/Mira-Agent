from __future__ import annotations

from typing import Any

from .profile_models import RoleProfile

CURRENT_MANIFEST_VERSION = 3


def migrate_manifest_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Normalize a legacy role manifest into v3 without dropping role-owned data."""

    version = int(payload.get("version") or 0)
    roles = payload.get("roles")
    if not isinstance(roles, list):
        raise ValueError("角色清单格式无效：roles 必须是数组")
    for item in roles:
        if not isinstance(item, dict):
            raise ValueError("角色清单格式无效：角色记录必须是对象")

    if version == CURRENT_MANIFEST_VERSION:
        return {"version": CURRENT_MANIFEST_VERSION, "roles": roles}, False
    if version != 2:
        raise ValueError(
            f"角色清单版本不支持：需要版本 {CURRENT_MANIFEST_VERSION}，实际为 {version}"
        )

    migrated_roles: list[dict[str, Any]] = []
    for item in roles:
        role = dict(item)
        if not isinstance(role.get("profile"), dict):
            role["profile"] = RoleProfile.from_legacy(
                system_prompt=str(role.get("system_prompt") or ""),
                background=str(role.get("background") or ""),
            ).to_dict()
        migrated_roles.append(role)
    return {"version": CURRENT_MANIFEST_VERSION, "roles": migrated_roles}, True
