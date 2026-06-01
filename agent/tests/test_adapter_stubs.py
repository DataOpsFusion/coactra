import pytest

from coactra.agent.adapters._stub import MissingExtraError
from coactra.agent.adapters.a2a import A2ATransport
from coactra.agent.adapters.fastmcp import FastMCPServer
from coactra.agent.adapters.keycloak import KeycloakExchanger


@pytest.mark.parametrize(
    "cls,extra",
    [
        (FastMCPServer, "mcp"),
        (A2ATransport, "a2a"),
        (KeycloakExchanger, "oauth"),
    ],
)
def test_stub_instantiation_raises_until_extra_and_impl_land(cls, extra):
    with pytest.raises(MissingExtraError, match=extra):
        cls()


def test_stubs_name_the_seam_they_will_satisfy():
    assert FastMCPServer.satisfies == "MCPServerPort"
    assert A2ATransport.satisfies == "A2ATransportPort"
    assert KeycloakExchanger.satisfies == "TokenExchanger"
