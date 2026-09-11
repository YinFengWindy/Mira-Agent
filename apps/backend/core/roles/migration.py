from __future__ import annotations

from typing import Any

from .profile_models import RoleProfile

CURRENT_MANIFEST_VERSION = 4


def migrate_manifest_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Normalize a legacy role manifest into v4 without dropping role-owned data."""

    version = int(payload.get("version") or 0)
    roles = payload.get("roles")
    if not isinstance(roles, list):
        raise ValueError("角色清单格式无效：roles 必须是数组")
    for item in roles:
        if not isinstance(item, dict):
            raise ValueError("角色清单格式无效：角色记录必须是对象")

    if version == CURRENT_MANIFEST_VERSION:
        return dict(payload), False
    if version not in {2, 3}:
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
    # Upgrade-only knowledge: capture fields before RoleRecord drops them, even
    # when the plugin is disabled. One atomic manifest replacement contains both
    # the destination namespace and removal of the legacy source fields.
    plugin_data = dict(payload.get("plugin_data") or {})
    pet_data = dict(plugin_data.get("desktop_pet") or {})
    pet_fields = ("pet_packages", "selected_pet_package_id", "desktop_pet_enabled")
    for role in migrated_roles:
        if any(key in role for key in pet_fields):
            pet_data.setdefault(
                str(role["id"]), {key: role.get(key) for key in pet_fields}
            )
            for key in pet_fields:
                role.pop(key, None)
    if pet_data:
        plugin_data["desktop_pet"] = pet_data
    return {
        **payload,
        "version": CURRENT_MANIFEST_VERSION,
        "roles": migrated_roles,
        "plugin_data": plugin_data,
    }, True
