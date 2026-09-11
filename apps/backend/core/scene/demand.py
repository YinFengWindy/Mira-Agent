"""Explicit per-role demand for the shared observation service."""

from collections.abc import Callable

from core.roles.models import RoleRecord


class SceneObservationDemand:
    """Generation-local consumer predicates; registration returns its disposer."""

    def __init__(self) -> None:
        self._consumers: dict[object, Callable[[RoleRecord], bool]] = {}

    def register(self, predicate: Callable[[RoleRecord], bool]) -> Callable[[], None]:
        """Registers demand without starting observation or retaining plugin contexts."""
        key = object()
        self._consumers[key] = predicate

        def dispose() -> None:
            self._consumers.pop(key, None)

        return dispose

    def needed(self, role: RoleRecord) -> bool:
        """Reports whether any installed consumer requests this role's observations."""
        return any(predicate(role) for predicate in self._consumers.values())
