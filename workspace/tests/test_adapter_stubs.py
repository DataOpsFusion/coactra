import pytest

from fleetlib.workspace.adapters._stub import MissingExtraError
from fleetlib.workspace.adapters.daytona import DaytonaBackend
from fleetlib.workspace.adapters.e2b import E2BBackend
from fleetlib.workspace.adapters.openhands import OpenHandsBackend


@pytest.mark.parametrize(
    "cls,extra",
    [
        (DaytonaBackend, "daytona"),
        (E2BBackend, "e2b"),
        (OpenHandsBackend, "openhands"),
    ],
)
def test_stub_instantiation_raises_until_extra_and_impl_land(cls, extra):
    # Stubs import fine WITHOUT the extra (no real SDK imported at module top),
    # but instantiating one tells you exactly which extra to install.
    with pytest.raises(MissingExtraError, match=extra):
        cls()
