import pytest

from coactra.workflow.adapters._stub import MissingExtraError
from coactra.workflow.adapters.prefect import PrefectEngine
from coactra.workflow.adapters.temporal import TemporalEngine


@pytest.mark.parametrize("cls,extra", [
    (TemporalEngine, "temporal"),
    (PrefectEngine, "prefect"),
])
def test_stub_instantiation_raises_until_extra_and_impl_land(cls, extra):
    with pytest.raises(MissingExtraError, match=extra):
        cls()


def test_stubs_name_the_engine_seam_they_will_satisfy():
    assert TemporalEngine.satisfies == "WorkflowEngine"
    assert PrefectEngine.satisfies == "WorkflowEngine"
