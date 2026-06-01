import pytest

from fleetlib.memory import Capability
from fleetlib.memory.adapters._stub import MissingExtraError
from fleetlib.memory.adapters.graphiti import GraphitiBackend
from fleetlib.memory.adapters.letta import LettaBackend
from fleetlib.memory.adapters.mem0 import Mem0Backend


def test_stubs_declare_capabilities_without_the_extra():
    # Capability declaration is metadata — available even when the optional dep is absent.
    assert Capability.GRAPH_EDGES in GraphitiBackend.declared_capabilities
    assert Capability.MEMORY_BLOCK in LettaBackend.declared_capabilities
    assert Capability.VECTOR_EMBEDDING in Mem0Backend.declared_capabilities


@pytest.mark.parametrize("cls,extra", [
    (Mem0Backend, "mem0"),
    (GraphitiBackend, "graphiti"),
    (LettaBackend, "letta"),
])
def test_stub_instantiation_raises_until_extra_and_impl_land(cls, extra):
    with pytest.raises(MissingExtraError, match=extra):
        cls()
