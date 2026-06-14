from coactra.errors import ConfigError
from coactra.team.directory import CrossTenantError
from coactra.team.directory.errors import MissingExtraError


def test_cross_tenant_error_is_value_error():
    # Callers may catch it as ValueError; it is a precise, named isolation breach.
    assert issubclass(CrossTenantError, ValueError)


def test_missing_extra_error_is_config_error():
    assert issubclass(MissingExtraError, ConfigError)
