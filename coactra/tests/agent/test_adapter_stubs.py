from coactra.agent.adapters.a2a import A2ATransport
from coactra.agent.adapters.keycloak import KeycloakExchanger


def test_adapters_name_the_seam_they_satisfy():
    assert A2ATransport.satisfies == "AsyncA2ATransportPort"
    assert KeycloakExchanger.satisfies == "TokenExchanger"
