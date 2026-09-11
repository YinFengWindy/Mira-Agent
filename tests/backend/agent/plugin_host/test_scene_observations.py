import gc
import weakref
from types import SimpleNamespace

import pytest

from agent.plugin_host.effects import EffectScope
from agent.plugin_host.scene_observations import SceneObservationsCapability
from core.scene.demand import SceneObservationDemand


@pytest.mark.asyncio
async def test_rollback_revokes_role_demand_and_releases_plugin_consumer():
    class Consumer:
        def wants(self, role):
            return role.id == "mira"

    consumer = Consumer()
    reference = weakref.ref(consumer)
    demand = SceneObservationDemand()
    scope = EffectScope("consumer")
    capability = SceneObservationsCapability(demand, scope)
    capability.request(consumer.wants)
    assert demand.needed(SimpleNamespace(id="mira"))
    assert not demand.needed(SimpleNamespace(id="other"))
    del consumer
    assert reference() is not None
    assert await scope.dispose_all() == []
    gc.collect()
    assert reference() is None
    assert not demand.needed(SimpleNamespace(id="mira"))
    with pytest.raises(RuntimeError, match="已处置"):
        capability.request(lambda _: True)
    assert not demand.needed(SimpleNamespace(id="mira"))
