import coactra.work as w


def test_public_surface_is_exact():
    expected = {
        "__version__", "AgentSpec", "ApprovalRequest", "Artifact", "ArtifactPart",
        "ArtifactRef", "ArtifactStore", "Assignment", "Attempt", "AttemptStatus", "AuditSink", "Budget",
        "CapabilityDescriptor", "CapabilityRequirement", "CapabilitySet", "Checkpoint",
        "ConflictError", "Deadline", "Decision", "DecisionOutcome", "ElicitationRequest",
        "EventEnvelope", "InMemoryWorkStore", "InvalidTransitionError", "Lease", "LeaseError",
        "Provenance", "ResumeToken", "RetryPolicy", "Scope", "SkillSpec", "Usage", "WorkError",
        "WorkManager", "WorkNotFoundError", "WorkOrder", "WorkStatus", "WorkStore",
    }
    assert set(w.__all__) == expected
