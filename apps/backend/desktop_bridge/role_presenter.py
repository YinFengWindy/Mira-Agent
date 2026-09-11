from __future__ import annotations

from typing import Any


class DesktopRolePresenter:
    """Builds desktop-safe role payloads without owning role operations."""

    def __init__(self, role_store: Any, relationship_runtime: Any | None = None) -> None:
        self._role_store = role_store
        self._relationship_runtime = relationship_runtime

    def serialize(self, role: Any) -> dict[str, Any]:
        """Returns role fields plus desktop asset and runtime state views."""
        payload = role.to_dict()
        avatar = payload.get("avatar")
        illustrations = payload.get("illustrations") or []
        payload["avatar_abs"] = (
            str((self._role_store.roles_dir / avatar).resolve())
            if isinstance(avatar, str) and avatar
            else None
        )
        chat_background = payload.get("chat_background")
        payload["chat_background_abs"] = (
            str((self._role_store.roles_dir / chat_background).resolve())
            if isinstance(chat_background, str) and chat_background
            else None
        )
        payload["illustrations_abs"] = [
            str((self._role_store.roles_dir / relative_path).resolve())
            for relative_path in illustrations
            if isinstance(relative_path, str) and relative_path
        ]
        # Pet packages are no longer enriched here (#181-D). The two absolute
        # paths this used to add — `spritesheet_abs` / `preview_abs` — are how
        # the desktop grants `shiori-asset://` URLs, and the only consumer left
        # is the pet's own package manager, which gets them from
        # `plugin.desktop_pet.pets.list`. Emitting them on every role payload
        # meant every `roles.list` leaked pet asset paths to a renderer that had
        # no use for them.
        #
        # `role.to_dict()` still carries the raw `pet_packages` field; it goes
        # when the pet's data leaves `RoleRecord` altogether.
        if self._relationship_runtime is not None:
            snapshot = self._relationship_runtime.read_snapshot(role.id)
            runtime = self._relationship_runtime.current_loneliness_runtime(role.id)
            if snapshot is not None:
                payload["relationship_snapshot"] = snapshot
            if runtime is not None:
                payload["loneliness_runtime"] = runtime
        return payload
