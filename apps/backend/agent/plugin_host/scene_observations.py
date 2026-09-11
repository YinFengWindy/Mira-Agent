"""Effect-scoped access to the shared core scene observation demand."""

from collections.abc import Callable

from agent.plugin_host.effects import EffectScope
from core.roles.models import RoleRecord
from core.scene.demand import SceneObservationDemand


class SceneObservationsCapability:
    """Lets a consumer request observations while its plugin effects remain alive."""

    def __init__(self, demand: SceneObservationDemand, effects: EffectScope) -> None:
        self._demand = demand
        self._effects = effects

    def request(self, predicate: Callable[[RoleRecord], bool]) -> None:
        """Adds one demand and automatically revokes it on unload or setup rollback."""
        dispose = self._demand.register(predicate)
        try:
            self._effects.add("scene_observations", dispose)
        except BaseException:
            dispose()
            raise
