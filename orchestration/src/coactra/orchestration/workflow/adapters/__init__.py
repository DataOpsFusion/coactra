"""Optional-extra workflow runtime adapters.

Adapters keep third-party runtime APIs below Coactra's stable ``WorkflowEngine``
contract. Production suitability depends on the adapter maturity and host runtime
configuration documented in ``docs/ADAPTER_MATURITY.md``.
"""
from coactra.orchestration.workflow.adapters._stub import MissingExtraError
from coactra.orchestration.workflow.adapters.prefect import PrefectEngine
from coactra.orchestration.workflow.adapters.temporal import TemporalEngine

__all__ = ["MissingExtraError", "PrefectEngine", "TemporalEngine"]
