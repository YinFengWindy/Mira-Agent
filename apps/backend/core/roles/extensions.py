"""Opaque plugin role state participating in the manifest's atomic save.

Physical colocation is intentional: plugins own their schemas, validation and
projections while role edits and cross-role plugin changes have one commit point.
No extension data belongs to RoleRecord or runtime_config.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from .manifest import RoleManifestRepository

# A participant mutates only its detached namespace; persistence is the caller's.
DraftWriter = Callable[[str, dict[str, Any], dict[str, Any]], None]
Projector = Callable[[str, dict[str, Any]], dict[str, Any]]


class RoleExtensions:
    """Coordinates active plugin draft participants without interpreting schemas."""

    def __init__(self, repository: RoleManifestRepository) -> None:
        self._repository = repository
        self._participants: dict[str, tuple[DraftWriter, Projector]] = {}

    def register(self, plugin_id: str, write: DraftWriter, project: Projector):
        """Registers a save participant and returns its lifecycle disposer."""
        if plugin_id in self._participants:
            raise ValueError(f"角色扩展已注册: {plugin_id}")
        participant = (write, project)
        self._participants[plugin_id] = participant

        def dispose() -> None:
            if self._participants.get(plugin_id) is participant:
                del self._participants[plugin_id]

        return dispose

    def read(self, plugin_id: str) -> dict[str, Any]:
        """Returns detached data under the canonical manifest lock."""
        with self._repository.lock:
            return deepcopy(
                self._repository.load_payload()
                .get("plugin_data", {})
                .get(plugin_id, {})
            )

    def update(self, plugin_id: str, mutate: Callable[[dict[str, Any]], None]) -> None:
        """Atomically updates one namespace while preserving roles and other plugins."""
        with self._repository.lock:
            payload = self._repository.load_payload()
            data = deepcopy(payload.get("plugin_data", {}))
            mutate(data.setdefault(plugin_id, {}))
            self._repository.save_payload(payload["roles"], plugin_data=data)

    def prepare_save(
        self, role_id: str, drafts: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Validates all supplied drafts before the role save's atomic commit."""
        with self._repository.lock:
            data = deepcopy(self._repository.load_payload().get("plugin_data", {}))
            for plugin_id, values in (drafts or {}).items():
                participant = self._participants.get(plugin_id)
                if participant is None:
                    raise ValueError(f"角色扩展不可用: {plugin_id}")
                if not isinstance(values, dict):
                    raise ValueError(f"角色扩展草稿必须是对象: {plugin_id}")
                participant[0](role_id, values, data.setdefault(plugin_id, {}))
            return data

    def project(self, role_id: str) -> dict[str, Any]:
        """Projects active plugin snapshots separately from the core role record."""
        with self._repository.lock:
            data = self._repository.load_payload().get("plugin_data", {})
            return {
                plugin_id: project(role_id, deepcopy(data.get(plugin_id, {})))
                for plugin_id, (_, project) in self._participants.items()
            }
