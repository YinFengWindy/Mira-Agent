"""``plugin.desktop_pet.*`` RPC handlers: which role and package the pet renders.

Ported from the Electron main process (#181-C). Before this, `main.ts`'s
``resolveDesktopPetBinding`` called the core ``roles.list`` method and reached
into the role payload for ``pet_packages`` / ``selected_pet_package_id`` /
``desktop_pet_enabled`` — pet domain knowledge sitting in the host, which is
exactly what #181 set out to remove. The pet's controller now runs in the
plugin host renderer and has no way to call core bridge methods: ``ctx.rpc``
only reaches this plugin's own ``plugin.desktop_pet.*`` namespace. So the
lookup moves here, where the plugin already owns a ``RoleStore``.

``spritesheet_abs`` is deliberately named that way: it is one of the declared
trusted asset fields in ``apps/desktop/src/assets/localAssetPolicy.ts``, so the
desktop bridge grants it a ``shiori-asset://`` URL on the way out and the
renderer never sees a filesystem path it could not already reach.
"""

from __future__ import annotations

from typing import Any

from core.roles.models import RolePetPackage, RoleRecord
from core.roles.store import RoleStore


class DesktopPetRpcHandlers:
    """Owns request/response shaping for every ``plugin.desktop_pet.*`` method."""

    def __init__(self, *, role_store: RoleStore) -> None:
        self._role_store = role_store

    async def binding_get(self, payload: dict[str, Any]) -> dict[str, Any]:
        """``plugin.desktop_pet.binding.get``: the role/package pair to render.

        ``role_id`` is optional. Without it the pet-enabled role is used — at
        most one role can have ``desktop_pet_enabled`` set (``pet_state.py``
        clears the others on write). With it, the named role is returned even
        when its pet is switched off, matching the caller that passes a role
        id: it is re-resolving a binding it already decided to show.

        Returns ``{"binding": None}`` rather than raising when nothing is
        bound: "no role has a pet package selected" is the ordinary state of a
        fresh install, not a failure the caller should surface as an error.
        """
        role_id = str(payload.get("role_id") or "").strip()
        role = self._resolve_role(role_id)
        if role is None:
            return {"binding": None}
        package = self._selected_package(role)
        if package is None:
            return {"binding": None}
        spritesheet = self._role_store.roles_dir / package.spritesheet_path
        if not spritesheet.is_file():
            return {"binding": None}
        return {
            "binding": {
                "role_id": role.id,
                "package": {
                    "id": package.id,
                    "display_name": package.display_name,
                    "spritesheet_abs": str(spritesheet.resolve()),
                },
                "actions": dict(package.actions),
            }
        }

    def _resolve_role(self, role_id: str) -> RoleRecord | None:
        if role_id:
            return self._role_store.get_role(role_id)
        return next(
            (role for role in self._role_store.list_roles() if role.desktop_pet_enabled),
            None,
        )

    @staticmethod
    def _selected_package(role: RoleRecord) -> RolePetPackage | None:
        if not role.selected_pet_package_id:
            return None
        return next(
            (
                item
                for item in role.pet_packages
                if item.id == role.selected_pet_package_id
            ),
            None,
        )
