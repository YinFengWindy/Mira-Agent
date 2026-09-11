"""Reconcile plugin state and abandoned pet assets across disable/enable cycles."""

from __future__ import annotations

import shutil

from bus.events_lifecycle import RoleDeleted
from core.roles.store import RoleStore

from .pet_state import PLUGIN_ID, RolePetStateStore
from .models import RolePetState


class PetStateReconciler:
    """Cleans deleted roles even if their deletion happened while disabled."""

    def __init__(self, roles: RoleStore) -> None:
        self._roles = roles

    def reconcile(self) -> None:
        """Prunes missing roles and orphan package directories under one lock."""
        with self._roles.lock:
            roles = self._roles.list_roles()
            role_ids = {role.id for role in roles}

            def prune(data):
                for role_id in list(data):
                    if role_id not in role_ids:
                        del data[role_id]
                enabled = False
                for role in roles:
                    if role.id not in data:
                        continue
                    state = RolePetState.from_dict(role.id, data[role.id])
                    state.desktop_pet_enabled = (
                        state.desktop_pet_enabled and not enabled
                    )
                    enabled = enabled or state.desktop_pet_enabled
                    data[role.id] = state.to_dict()

            self._roles.extensions.update(PLUGIN_ID, prune)
            states = {
                role.id: role for role in RolePetStateStore(self._roles).list_roles()
            }
            for asset_dir in self._roles.assets_dir.iterdir():
                pets = asset_dir / "pets"
                if not pets.is_dir() or pets.is_symlink() or asset_dir.is_symlink():
                    continue
                state = states.get(asset_dir.name)
                if state is None:
                    shutil.rmtree(pets)
                    continue
                installed = (
                    {package.id for package in state.pet_packages} if state else set()
                )
                for package_dir in pets.iterdir():
                    if (
                        package_dir.name not in installed
                        and package_dir.is_dir()
                        and not package_dir.is_symlink()
                    ):
                        shutil.rmtree(package_dir)

    async def on_role_deleted(self, _event: RoleDeleted) -> None:
        """Runs the same idempotent cleanup for live lifecycle notifications."""
        self.reconcile()
