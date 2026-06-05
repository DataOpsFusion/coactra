"""Optional-extra workflow runtime adapters.

Adapters keep third-party runtime APIs below Coactra's stable ``WorkflowEngine``
contract. Production suitability depends on host runtime configuration (e.g. a
persistent checkpointer and stable thread id for durable resume).
"""
from coactra.jobs.workflow.adapters._stub import MissingExtraError
from coactra.jobs.workflow.adapters.prefect import PrefectEngine
from coactra.jobs.workflow.adapters.temporal import TemporalEngine

__all__ = ["MissingExtraError", "PrefectEngine", "TemporalEngine"]
