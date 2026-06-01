from fleetlib.organization import CrossTenantError
from fleetlib.organization.errors import MissingExtraError


def test_cross_tenant_error_is_value_error():
    # Callers may catch it as ValueError; it is a precise, named isolation breach.
    assert issubclass(CrossTenantError, ValueError)


def test_missing_extra_error_is_runtime_error():
    assert issubclass(MissingExtraError, RuntimeError)
